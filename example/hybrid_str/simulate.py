import numpy as np
import matplotlib.pyplot as plt


# ============================================================
# STR PA Hybrid Neutralization Simulation
# ============================================================


# -----------------------------
# Parameters
# -----------------------------

LS1 = 0.20
LS2 = 0.60
LS3 = 0.90


Fa = 5.0e-3       # HCl flow
Fb = 3.0e-3       # NaOH flow
Fd = 6.0e-3       # discharge flow


CHCl = 0.05
CNaOH = 0.10



# -----------------------------
# Initial condition
# -----------------------------

V = LS1

pH_initial = 1.3

CH = 10**(-pH_initial)



# -----------------------------
# Simulation settings
# -----------------------------

dt = 0.001

t_end = 3000



# ============================================================
# Modes
# ============================================================

q0 = "q0_IDLE"
q1 = "q1_FILLING"
q2 = "q2_MIXING"
q3 = "q3_NEUTRALIZATION"
q4 = "q4_PARTIAL_DISCHARGE"
q5 = "q5_COMPLETE_DISCHARGE"


mode = q1

previous_mode = mode



# ============================================================
# Storage
# ============================================================

time = []
volume = []
pH_history = []

transition_log = []


mode_entry_time = 0.0



t = 0



# ============================================================
# Simulation loop
# ============================================================

while t <= t_end:


    CH = max(CH,1e-12)

    pH = -np.log10(CH)



    # -----------------------------
    # Actuator defaults
    # -----------------------------

    VA_CV_001 = "CLOSED"
    VA_CV_002 = "CLOSED"
    VA_CV_003 = "CLOSED"
    VA_CV_004 = "CLOSED"

    stirrer = "OFF"


    acid = False
    base = False
    drain = False



    trigger = ""



    # ========================================================
    # q1 Filling
    # ========================================================

    if mode == q1:


        VA_CV_001 = "OPEN"

        acid = True


        if V >= LS2:

            trigger = "Liquid level reached LS2"

            mode = q2



    # ========================================================
    # q2 Mixing
    # ========================================================

    elif mode == q2:


        stirrer = "ON"


        if pH < 6.5:

            trigger = "pH below target range"

            mode = q3


        elif pH >= 6.5:

            trigger = "Desired pH achieved"

            mode = q5



    # ========================================================
    # q3 Neutralization
    # ========================================================

    elif mode == q3:


        stirrer = "ON"


        VA_CV_001 = "OPEN"

        VA_CV_002 = "OPEN"


        acid = True

        base = True



        if pH >= 6.5:

            trigger = "pH reached neutralization target"

            mode = q5



        elif V >= LS3:

            trigger = "Liquid level reached LS3"

            mode = q4



    # ========================================================
    # q4 Partial discharge
    # ========================================================

    elif mode == q4:


        stirrer = "ON"

        VA_CV_004 = "OPEN"

        drain = True



        if V <= LS2:

            trigger = "Liquid level decreased to LS2"

            mode = q2



    # ========================================================
    # q5 Complete discharge
    # ========================================================

    elif mode == q5:


        VA_CV_003 = "OPEN"

        drain = True



        if V <= LS1:

            trigger = "Liquid level reached LS1"

            mode = q0



    # ========================================================
    # q0 Idle
    # ========================================================

    elif mode == q0:

        break



    # ========================================================
    # Transition logging
    # ========================================================

    if mode != previous_mode:


        duration = t - mode_entry_time



        print("\n====================================")

        print(
            f"Mode: {previous_mode}"
        )

        print(
            f"Entry time : {mode_entry_time:.3f} s"
        )

        print(
            f"Exit time  : {t:.3f} s"
        )

        print(
            f"Duration   : {duration:.3f} s"
        )

        print(
            f"Trigger    : {trigger}"
        )

        print(
            f"Volume     : {V:.3f} m3"
        )

        print(
            f"pH         : {pH:.3f}"
        )

        print(
            f"Transition : {previous_mode} --> {mode}"
        )


        print("\nActuators after transition:")

        print(
            f"VA-CV-001 HCl       : {VA_CV_001}"
        )

        print(
            f"VA-CV-002 NaOH      : {VA_CV_002}"
        )

        print(
            f"VA-CV-003 Discharge : {VA_CV_003}"
        )

        print(
            f"VA-CV-004 Partial   : {VA_CV_004}"
        )

        print(
            f"Stirrer             : {stirrer}"
        )


        transition_log.append(
            [
                previous_mode,
                mode,
                mode_entry_time,
                t,
                duration,
                trigger,
                V,
                pH
            ]
        )


        mode_entry_time = t

        previous_mode = mode



    # ========================================================
    # Continuous dynamics
    # ========================================================


    Fin = 0


    if acid:

        Fin += Fa


    if base:

        Fin += Fb



    Fout = Fd if drain else 0



    dVdt = Fin - Fout



    dCHdt = (

        (Fa if acid else 0)
        *
        (CHCl - CH)

        -

        (Fb if base else 0)
        *
        (CNaOH + CH)

    ) / max(V,1e-8)



    V += dVdt*dt

    CH += dCHdt*dt


    V = max(V,0)

    CH = max(CH,1e-12)



    time.append(t)

    volume.append(V)

    pH_history.append(-np.log10(CH))


    t += dt



# ============================================================
# Final summary
# ============================================================

print("\n\n========== FINAL RESULT ==========")

print("Final mode:", mode)

print(
    "Maximum pH:",
    max(pH_history)
)

print(
    "Time of maximum pH:",
    time[np.argmax(pH_history)]
)

print(
    "Final volume:",
    volume[-1]
)



print("\n\n========== MODE SUMMARY ==========")

for tr in transition_log:

    print(
        f"{tr[0]} --> {tr[1]} | "
        f"duration={tr[4]:.3f}s | "
        f"trigger={tr[5]} | "
        f"V={tr[6]:.3f}m3 | "
        f"pH={tr[7]:.3f}"
    )



# ============================================================
# Plots
# ============================================================

plt.figure(figsize=(10,5))

plt.plot(time,pH_history,label="pH")

plt.axhline(
    6.5,
    linestyle="--",
    color="green",
    label="pH=6.5"
)

plt.axhline(
    7.5,
    linestyle="--",
    color="red",
    label="pH=7.5"
)


plt.xlabel("Time (s)")
plt.ylabel("pH")

plt.title("STR Neutralization pH")

plt.grid()

plt.legend()

plt.show()



plt.figure(figsize=(10,5))

plt.plot(time,volume,label="Volume")

plt.axhline(
    LS2,
    linestyle="--",
    label="LS2"
)

plt.axhline(
    LS3,
    linestyle="--",
    label="LS3"
)


plt.xlabel("Time (s)")
plt.ylabel("Volume (m3)")

plt.title("STR Liquid Level")

plt.grid()

plt.legend()

plt.show()