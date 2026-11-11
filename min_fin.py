from ortools.sat.python import cp_model
import random

# --- CONFIGURATION DU SERVICE ---
horizon = 540  # 8h00 à 17h00
nb_patients_pool = 90 
pools = {
    "Machines": ["Machine_A", "Machine_B"],
    "Medecins": ["Docteur_1", "Docteur_2", "Docteur_3", "Docteur_4"]
}

# Shifts des médecins (Début, Fin) par rapport à 8h00
shifts_medecins = {
    "Docteur_1": (0, 420),    # 08h - 15h
    "Docteur_2": (60, 480),   # 09h - 16h
    "Docteur_3": (60, 480),   # 09h - 16h
    "Docteur_4": (120, 540)   # 10h - 17h
}

random.seed(123)
patients_data = []

pathologies = ["Uro", "Sein_Simple", "Sein_Complexe", "Autres", "Hospitalise"]
poids = [25, 30, 15, 20, 10]

# --- GÉNÉRATION DES PATIENTS (PROTOCOLE RÉEL) ---
for i in range(nb_patients_pool):
    type_p = random.choices(pathologies, weights=poids, k=1)[0]
    is_first = random.random() < 0.066 # Max 6 nouveaux/jour
    is_mob = random.random() < 0.05
    est_bran = random.random() < 0.02
    nettoyage = random.random() < 0.03 

    duree = 20 if type_p in ["Sein_Complexe", "Hospitalise"] else 10
    if is_mob or is_first : duree += 10
    if est_bran: duree += 20
    if nettoyage: duree += 15

    patients_data.append({
        "id": f"P_{i:02d}", "duree": duree, "type": type_p,
        "is_hosp": (type_p == "Hospitalise"), "is_mob": is_mob,
        "is_bran": est_bran, "is_first": is_first
    })

def resoudre_capacite_par_machine():
    model = cp_model.CpModel()
    intervalles_machines = {m: [] for m in pools["Machines"]}
    intervalles_medecins = {doc: [] for doc in pools["Medecins"]}
    variables_affichage = {} 
    tous_les_choix = []

    # --- 1. PAUSES & MAINTENANCE (FIXES POUR LA VITESSE) ---
    # Maintenance Machine A (10h-11h)
    #maint_A = model.NewIntervalVar(120, 60, 180, "maint_A")
    #intervalles_machines["Machine_A"].append(maint_A)

    # Pauses déjeuner (1h fixe au milieu du shift)
    for doc in pools["Medecins"]:
        s_s, e_s = shifts_medecins[doc]
        milieu = (s_s + e_s) // 2 - 30
        p_int = model.NewIntervalVar(milieu, 60, milieu + 60, f"pause_{doc}")
        intervalles_medecins[doc].append(p_int)

    # --- 2. LOGIQUE PATIENTS ---
    for p in patients_data:
        est_pris = model.NewBoolVar(f"pris_{p['id']}")
        tous_les_choix.append(est_pris)
        start_v = model.NewIntVar(0, horizon, f"start_{p['id']}")
        end_v = model.NewIntVar(0, horizon, f"end_{p['id']}")
        
        # Contraintes Priorité 1 (Brancardiers 9h-17h)
        if p['is_hosp'] or p['is_mob'] or p['is_bran']:
            model.Add(start_v >= 60).OnlyEnforceIf(est_pris)
            model.Add(end_v <= 540).OnlyEnforceIf(est_pris)
        else:
            model.Add(end_v <= 540).OnlyEnforceIf(est_pris)

        # Couplage Machine
        pres_m = []
        for m in pools["Machines"]:
            pm = model.NewBoolVar(f"p_m_{p['id']}_{m}")
            pres_m.append(pm)
            iv = model.NewOptionalIntervalVar(start_v, p['duree'], end_v, pm, f"iv_m_{p['id']}_{m}")
            intervalles_machines[m].append(iv)
        model.Add(sum(pres_m) == est_pris)

        # Couplage Médecin
        pres_d = []
        for doc in pools["Medecins"]:
            pd = model.NewBoolVar(f"p_d_{p['id']}_{doc}")
            pres_d.append(pd)
            s_s, e_s = shifts_medecins[doc]
            model.Add(start_v >= s_s).OnlyEnforceIf(pd)
            model.Add(end_v <= e_s).OnlyEnforceIf(pd) # Note: end_var doit etre end_v
            
            iv = model.NewOptionalIntervalVar(start_v, p['duree'], end_v, pd, f"iv_d_{p['id']}_{doc}")
            intervalles_medecins[doc].append(iv)
        model.Add(sum(pres_d) == est_pris)

        variables_affichage[p['id']] = {
            "est_pris": est_pris, "debut": start_v, "fin": end_v, 
            "m_vars": pres_m, "d_vars": pres_d
        }

    # Contraintes de non-chevauchement
    for m in pools["Machines"]: model.AddNoOverlap(intervalles_machines[m])
    for d in pools["Medecins"]: model.AddNoOverlap(intervalles_medecins[d])

    # --- 3. OPTIMISATION ---
    model.Maximize(sum(tous_les_choix))

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 30.0
    status = solver.Solve(model)

    # --- 4. AFFICHAGE GROUPÉ PAR MACHINE ---
    if status in [cp_model.OPTIMAL, cp_model.FEASIBLE]:
        print(f"\n✅ CAPACITÉ TOTALE : {int(solver.ObjectiveValue())} PATIENTS TRAITÉS AVANT 17h00")
        
        # Récupération des données
        all_rdv = []
        for p_id, v in variables_affichage.items():
            if solver.Value(v["est_pris"]):
                m_nom = next(pools["Machines"][i] for i, var in enumerate(v["m_vars"]) if solver.Value(var))
                d_nom = next(pools["Medecins"][i] for i, var in enumerate(v["d_vars"]) if solver.Value(var))
                all_rdv.append({
                    "start": solver.Value(v["debut"]),
                    "end": solver.Value(v["fin"]),
                    "id": p_id,
                    "machine": m_nom,
                    "doc": d_nom
                })

        # Affichage Machine par Machine
        for machine in pools["Machines"]:
            print(f"\n>>>> PLANNING {machine} :")
            print(f"{'CRÉNEAU':<15} | {'PATIENT':<10} | {'MÉDECIN'}")
            print("-" * 45)
            
            # On filtre pour la machine actuelle et on trie par heure
            planning_machine = sorted([r for r in all_rdv if r['machine'] == machine], key=lambda x: x['start'])
            
            for r in planning_machine:
                h_start = f"{r['start']//60+8:02d}h{r['start']%60:02d}"
                h_end = f"{r['end']//60+8:02d}h{r['end']%60:02d}"
                print(f"{h_start} - {h_end} | {r['id']:<10} | {r['doc']}")
            
        print("\n" + "="*60 + "\n")
    else:
        print("❌ Problème trop complexe. Réduisez le pool de patients ou augmentez le temps de calcul.")

resoudre_capacite_par_machine()