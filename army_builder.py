import streamlit as st
import pandas as pd
import random
import json
import math

# Load data from CSVs
ships_df = pd.read_csv("ships.csv")
captains_df = pd.read_csv("captains.csv")
fighters_df = pd.read_csv("fighters.csv")

# App title
st.title("Aetherstream: Leviathan Army Builder")

# Instructions block
with st.expander("📖 How to Use the Leviathan Army Builder"):
    st.markdown("""
### Building Your Force

1. **Select a faction** using the dropdown in the sidebar.
2. **Add ships** by choosing their count. You can add multiple of the same ship.
3. **Assign captains** in the same way as ships.

---

### Adding Fighter Groups

1. Choose a **fighter group type**: Flight (4 fighters) or Squadron (1–12 fighters).
2. Pick your **generation method**:
   - **Manual**: Choose fighter types and how many of each.
   - **Auto by Points**: Randomly fills a group up to a chosen PV limit.
   - **Random then Edit**: Auto-generates fighters, then lets you edit their counts.
3. Set a **pilot experience level**.
4. Optionally, name the group.
5. Click **"Add Fighter Group"**.

---

### Force Overview

- All units are shown in the main table.
- **Click ❌ to remove a fighter group**.
- Total PV is shown at the bottom.
- You can **download your force** as JSON or CSV.
    """)

# Sidebar
st.sidebar.header("Build Your Force")
faction = st.sidebar.selectbox("Select Faction", ships_df["Faction"].unique())

# Filter based on faction
filtered_ships = ships_df[ships_df["Faction"] == faction]
filtered_captains = captains_df[captains_df["Faction"] == faction]
filtered_fighters = fighters_df[fighters_df["Faction"] == faction]

# Allow multiple of the same ship
ship_counts = {}
for ship_name in filtered_ships["Ship Name"]:
    count = st.sidebar.number_input(f"{ship_name} (PV {filtered_ships[filtered_ships['Ship Name'] == ship_name]['Cost'].values[0]})", 0, 10, 0, key=f"ship_{ship_name}")
    if count > 0:
        ship_counts[ship_name] = count

# Allow multiple of the same captain
captain_counts = {}
for captain_name in filtered_captains["Name"]:
    count = st.sidebar.number_input(f"{captain_name} (PV {filtered_captains[filtered_captains['Name'] == captain_name]['Cost'].values[0]})", 0, 10, 0, key=f"captain_{captain_name}")
    if count > 0:
        captain_counts[captain_name] = count

# Fighter creation method
st.sidebar.markdown("---")
st.sidebar.subheader("Fighter Group Creator")
fighter_method = st.sidebar.radio("Fighter Group Setup", ["Manual", "Auto by Points", "Random then Edit"])
group_type = st.sidebar.radio("Fighter Group Type", ["Flight", "Squadron"])
fighter_group_name = st.sidebar.text_input("Optional Name for Fighter Group")

# Pilot Experience Level
experience_level = st.sidebar.selectbox("Pilot Experience", ["Green", "Rookie", "Regular", "Veteran", "Elite"])
experience_cost_map = {
    "Green": 0,
    "Rookie": 1,
    "Regular": 2,
    "Veteran": 3,
    "Elite": 4
}

# Session state to store fighter groups
if "fighter_groups" not in st.session_state:
    st.session_state.fighter_groups = []

fighter_selections = []

# Fighter selection logic
if fighter_method == "Manual":
    max_size = 4 if group_type == "Flight" else 12
    current_total = 0
    for idx, row in filtered_fighters.iterrows():
        remaining = max_size - current_total
        if remaining <= 0:
            break
        count = st.sidebar.number_input(
            f"{row['Fighter']} (PV {row['COST']})", 
            0, remaining, 0, key=f"manual_{row['Fighter']}"
        )
        if count > 0:
            fighter_selections.extend([row["Fighter"]] * count)
            current_total += count

elif fighter_method == "Auto by Points":
    max_points = st.sidebar.number_input("Max Points for Fighters", 0, 100, 10)
    size_limit = 4 if group_type == "Flight" else 12
    total = 0
    while total < max_points and len(fighter_selections) < size_limit:
        row = filtered_fighters.sample(1).iloc[0]
        if total + row["COST"] <= max_points:
            fighter_selections.append(row["Fighter"])
            total += row["COST"]

elif fighter_method == "Random then Edit":
    size = 4 if group_type == "Flight" else 12
    for i in range(size):
        row = filtered_fighters.sample(1, replace=True).iloc[0]
        default_count = st.sidebar.number_input(
            f"{row['Fighter']} (PV {row['COST']})", 
            0, size, 1, key=f"random_{i}_{row['Fighter']}_{i}"
        )
        fighter_selections.extend([row["Fighter"]] * default_count)
        if len(fighter_selections) >= size:
            fighter_selections = fighter_selections[:size]
            break

# Round up function
round_up = lambda x: math.ceil(x)

# Generate fighter group stats
def generate_fighter_group(fighter_names, group_type):
    subset = filtered_fighters[filtered_fighters["Fighter"].isin(fighter_names)]
    counts = pd.Series(fighter_names).value_counts()

    expanded = pd.concat([
        subset[subset["Fighter"] == name].iloc[[0]].copy().assign(count=count)
        for name, count in counts.items()
    ])

    for col in ["MAN", "DEF", "INT", "STR"]:
        expanded[col] = expanded[col] * expanded["count"]

    def compute_stat(col):
        if group_type == "Flight":
            return round_up(expanded[col].sum() / expanded["count"].sum())
        elif group_type == "Squadron":
            per_flight = max(1, int(len(fighter_names) / 3))
            flights = [fighter_names[i * per_flight:(i + 1) * per_flight] for i in range(3)]
            flight_averages = []
            for flight in flights:
                fsub = filtered_fighters[filtered_fighters["Fighter"].isin(flight)]
                c = pd.Series(flight).value_counts()
                fexp = pd.concat([
                    fsub[fsub["Fighter"] == n].iloc[[0]].copy().assign(count=cnt)
                    for n, cnt in c.items()
                ])
                fexp[col] = fexp[col] * fexp["count"]
                flight_averages.append(round_up(fexp[col].sum() / fexp["count"].sum()))
            return round_up(sum(flight_averages) / len(flight_averages))

    man = compute_stat("MAN")
    defense = compute_stat("DEF")
    intercept = compute_stat("INT")
    strafe = compute_stat("STR")

    ordnance = expanded["ORD"].dot(expanded["count"])
    qualities = ", ".join(sorted(set(q for q in expanded["Qualities"].dropna())))
    base_cost = round_up(expanded["COST"].sum())
    pilot_experience_cost = experience_cost_map[experience_level] * len(fighter_names)
    total_cost = round_up(base_cost + pilot_experience_cost)

    return {
        "Type": group_type,
        "Name": fighter_group_name if fighter_group_name else f"{group_type} Group",
        "Fighters": fighter_names,
        "MAN": man,
        "DEF": defense,
        "INT": intercept,
        "STR": strafe,
        "ORD": ordnance,
        "Qualities": qualities,
        "Experience": experience_level,
        "PV": total_cost
    }

# Add group button
if st.sidebar.button("Add Fighter Group"):
    size = len(fighter_selections)
    if group_type == "Flight" and size != 4:
        st.sidebar.error("A Flight must contain exactly 4 fighters.")
    elif group_type == "Squadron" and (size < 1 or size > 12):
        st.sidebar.error("A Squadron must contain between 1 and 12 fighters.")
    else:
        new_group = generate_fighter_group(fighter_selections, group_type)
        st.session_state.fighter_groups.append(new_group)
        st.sidebar.success(f"{group_type} added!")

# Build force list
force = []
total_pv = 0

for name, count in ship_counts.items():
    row = filtered_ships[filtered_ships["Ship Name"] == name].iloc[0]
    for _ in range(count):
        force.append({"Type": "Ship", "Ship Name": name, "PV": row["Cost"]})
        total_pv += row["Cost"]

for name, count in captain_counts.items():
    row = filtered_captains[filtered_captains["Name"] == name].iloc[0]
    for _ in range(count):
        force.append({"Type": "Captain", "Name": name, "PV": row["Cost"]})
        total_pv += row["Cost"]

st.subheader("Current Fighter Groups")
for i, fighter_group in enumerate(st.session_state.fighter_groups):
    cols = st.columns([5, 1])
    with cols[0]:
        st.write(fighter_group)
    with cols[1]:
        if st.button("❌", key=f"remove_{i}"):
            st.session_state.fighter_groups.pop(i)
            st.experimental_rerun()

for fighter_group in st.session_state.fighter_groups:
    force.append(fighter_group)
    total_pv += fighter_group["PV"]

# Main output
st.subheader("Current Force")
st.write(pd.DataFrame(force))
st.markdown(f"**Total PV: {total_pv}**")

# Export
st.download_button("Download JSON", data=json.dumps(force, indent=2), file_name="force.json")
st.download_button("Download CSV", data=pd.DataFrame(force).to_csv(index=False), file_name="force.csv")
