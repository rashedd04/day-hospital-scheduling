# Day-hospital treatment scheduling

Constraint-programming prototype that schedules one day of outpatient treatment sessions on shared machines and doctors, written in Python with Google OR-Tools (CP-SAT).

The question it answers: given a pool of patients waiting for a session, two treatment machines and four doctors on different shifts, how many patients can be treated between 8:00 and 17:00, and in what order?

Built in May 2026 during a research-initiation project (TER) on planning and scheduling in day hospitals at Grenoble INP – Génie Industriel, with the G-SCOP laboratory. All patient data is synthetic.

## The problem

| Element | Value in the model |
| --- | --- |
| Horizon | 8:00–17:00, in minutes (540) |
| Machines | 2, one patient at a time |
| Doctors | 4, each with a shift and a fixed 1-hour lunch break in the middle of it |
| Patients | pool of 90, generated with a fixed random seed |
| Pathology mix | urology 25%, simple breast 30%, complex breast 15%, other 20%, hospitalised 10% (sampling weights) |
| Session length | 10 minutes, or 20 for complex and hospitalised cases; +10 for a first session or reduced mobility, +20 for a stretcher patient, +15 for cleaning |
| Porter rule | hospitalised, reduced-mobility and stretcher patients cannot start before 9:00 |

Every treated patient needs one machine and one doctor for the whole session, inside that doctor's shift.

## The models

| File | What it does |
| --- | --- |
| `max_patients.py` | CP-SAT model. One optional interval per patient and machine, and per patient and doctor; no-overlap on every resource; objective: maximise the number of patients treated. 60-second limit. |
| `min_fin.py` | Same model on a second staffing scenario: doctors 2 and 3 work 9:00–16:00 instead of 8:00–15:00 and 10:00–17:00. 30-second limit. |
| `greedy.py` | Baseline without a solver: longest sessions first, each placed at the earliest minute where a machine and a doctor are both free. |

## Results

Outputs of one run on a 2-core machine are in [`results/`](results/).

| Model | Staffing | Patients treated (of 90) |
| --- | --- | --- |
| CP-SAT, `max_patients.py` | two doctors 8–15h, two 10–17h | 78 |
| CP-SAT, `min_fin.py` | one 8–15h, two 9–16h, one 10–17h | 69 |
| Greedy, `greedy.py` | two doctors 8–15h, two 10–17h | 61 |

The 90 generated sessions add up to 1,395 minutes against 1,080 machine-minutes, so treating everyone is impossible by construction; the models choose who fits.

## Limits to keep in mind

- The CP-SAT runs stop at a time limit and the scripts do not print whether the solution is proven optimal, so 78 and 69 are the best schedules found, and can change with the machine and the solver version.
- The greedy baseline is not an exact like-for-like comparison. It blocks Machine A for maintenance from 10:00 to 11:00 (disabled in the CP-SAT model) and does not draw the cleaning time, so its random patient pool differs.
- The file name `min_fin.py` is historical: the objective is still the number of patients treated, not the finishing time.
- One day, no uncertainty: no late arrivals, no-shows or machine breakdowns.

## Run it

```bash
pip install -r requirements.txt
python greedy.py
python max_patients.py   # up to 60 seconds
python min_fin.py        # up to 30 seconds
```

Each script prints the number of patients treated and the timetable of each machine (slot, patient, doctor). Parameters are constants at the top of each file.

## Next steps

- One shared patient generator and one configuration, so the three scripts solve exactly the same instance.
- Print the solver status and bound, and add the makespan as a second objective.
- Read the parameters from a file and export the schedule (CSV or a Gantt chart).

## Licence

MIT (see `LICENSE`).
