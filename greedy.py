import random

# --- CONFIGURATION (Identique au CP-SAT) ---
horizon = 540  # 8h00 à 17h00
nb_patients_pool = 90 
pools = {
    "Machines": ["Machine_A", "Machine_B"],
    "Medecins": ["Docteur_1", "Docteur_2", "Docteur_3", "Docteur_4"]
}

# Shifts réels des médecins
shifts_medecins = {
    "Docteur_1": (0, 420),    # 08h - 15h
    "Docteur_2": (0, 420),   # 09h - 16h
    "Docteur_3": (120, 540),   # 09h - 16h
    "Docteur_4": (120, 540)   # 10h - 17h
}

random.seed(123)
pathologies = ["Uro", "Sein_Simple", "Sein_Complexe", "Autres", "Hospitalise"]
poids = [25, 30, 15, 20, 10] 

# --- GÉNÉRATION DES DONNÉES PONDÉRÉES ---
patients_data = []
for i in range(nb_patients_pool):
    type_p = random.choices(pathologies, weights=poids, k=1)[0]
    is_first = random.random() < 0.066
    is_mob = random.random() < 0.05
    est_bran = random.random() < 0.02
    
    duree = 20 if type_p in ["Sein_Complexe", "Hospitalise"] else 10
    if is_mob or is_first : duree += 10
    if est_bran: duree += 20
    
    patients_data.append({
        "id": f"P_{i:02d}", "duree": duree, "type": type_p,
        "is_hosp": (type_p == "Hospitalise") or is_mob or est_bran
    })
    patients_data.sort(key=lambda x: x['duree'], reverse=True)

def algorithme_greedy_basique():
    # État des ressources (minute par minute)
    # 0 = libre, 1 = occupé
    planning_machines = {m: [0] * horizon for m in pools["Machines"]}
    planning_medecins = {d: [0] * horizon for d in pools["Medecins"]}
    
    for t in range(120, 180):
        planning_machines["Machine_A"][t] = 1

    # Bloquer les pauses déjeuner (1h au milieu du shift)
    for d in pools["Medecins"]:
        s_s, e_s = shifts_medecins[d]
        milieu = (s_s + e_s) // 2 - 30
        for t in range(milieu, milieu + 60):
            planning_medecins[d][t] = 1

    admis = []

    # On essaie de placer chaque patient un par un
    for p in patients_data:
        place_trouvee = False
        
        # On cherche le premier créneau possible (t)
        for t in range(0, horizon - p['duree']):
            # Respect de la contrainte Brancardiers (9h-17h)
            if p['is_hosp'] and t < 60:
                continue
                
            # Pour chaque minute de la séance
            for m in pools["Machines"]:
                if place_trouvee: break
                for d in pools["Medecins"]:
                    # Vérifier si le docteur travaille à cette heure
                    s_s, e_s = shifts_medecins[d]
                    if t < s_s or (t + p['duree']) > e_s:
                        continue
                        
                    # Vérifier si Machine et Docteur sont libres sur toute la durée
                    if all(planning_machines[m][t+k] == 0 for k in range(p['duree'])) and \
                       all(planning_medecins[d][t+k] == 0 for k in range(p['duree'])):
                        
                        # On réserve !
                        for k in range(p['duree']):
                            planning_machines[m][t+k] = 1
                            planning_medecins[d][t+k] = 1
                        
                        admis.append((t, t + p['duree'], p['id'], m, d))
                        place_trouvee = True
                        break
        if not place_trouvee:
            pass # Le patient est ignoré car pas de place immédiate

    # --- AFFICHAGE PAR MACHINE ---
    print(f"\n📊 RÉSULTAT ALGORITHME GREEDY : {len(admis)} patients admis")
    for m_nom in pools["Machines"]:
        print(f"\n>>>> PLANNING {m_nom} :")
        print(f"{'CRÉNEAU':<15} | {'PATIENT':<10} | {'MÉDECIN'}")
        print("-" * 45)
        machine_rdv = sorted([r for r in admis if r[3] == m_nom], key=lambda x: x[0])
        for s, e, pid, m, d in machine_rdv:
            print(f"{s//60+8:02d}h{s%60:02d} - {e//60+8:02d}h{e%60:02d} | {pid:<10} | {d}")

algorithme_greedy_basique()