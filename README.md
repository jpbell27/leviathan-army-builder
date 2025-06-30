# leviathan-army-builder
A trial army builder for FASA's Aetherstream Leviathan
(https://leviathan-army-builder-lgj9jngbxqlub27ajhi4n9.streamlit.app/)

🛠 How to Use the Aetherstream: Leviathan Army Builder

This Streamlit app allows you to quickly build and customize a legal force for Aetherstream: Leviathan, including capital ships, captains, and fighter groups (Flights and Squadrons).
🧭 Step-by-Step Guide
1. Choose Your Faction

    Use the dropdown at the top of the sidebar to select your faction.

    All ship, captain, and fighter options will be filtered to show only those from your selected faction.

2. Add Ships

    Scroll down to the Ship List in the sidebar.

    For each ship, use the number input to select how many copies to add.

    The ship's Point Value (PV) is displayed next to its name.

3. Add Captains

    Captains are listed below the ships.

    Use the number input to assign multiple captains (duplicates allowed).

    Their PV is shown next to each name.

4. Build Fighter Groups (Flights or Squadrons)

    Select a Fighter Group Type: either a Flight (exactly 4 fighters) or a Squadron (1–12 fighters).

    Choose a Pilot Experience Level: this affects cost, from Green (0) to Elite (4) points per fighter.

You can create fighter groups using one of three methods:

    Manual: Select specific fighter types and quantities manually (up to group max).

    Auto by Points: The app randomly selects fighters up to your specified PV cap.

    Random then Edit: A random group is generated and you can tweak individual fighter counts.

💡 Optional: Enter a custom name for your group (otherwise one is auto-generated).

📌 Stat Calculations:

    Fighter stats (Maneuver, Defense, Intercept, Strafe) are rounded up based on:

        Flights: stats are averaged across all fighters and rounded up.

        Squadrons: averages are calculated per 4-fighter flight, then averaged again and rounded up.

    ORD (Ordnance) is summed across all fighters—each contributes their full value.

    Fighter PV includes both base cost and experience level cost per pilot.

Press “Add Fighter Group” to add it to your force.
5. Review & Export Your Force

    The bottom of the app displays your full force in table format with total PV.

    Download options:

        JSON: for use in other tools or version control.

        CSV: easy to share or print.

⚠️ Notes & Limits

    Flights must contain exactly 4 fighters.

    Squadrons can contain 1 to 12 fighters.

    You can add multiple fighter groups, ships, and captains.


