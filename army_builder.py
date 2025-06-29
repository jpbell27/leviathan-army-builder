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
    count = st.sidebar.number_input(
        f"{ship_name} (PV {filtered_ships[filtered_ships['Ship Name'] == ship_name]['Cost'].values[0]})",
        0, 10, 0, key=f"ship_{ship_name}"
    )
    if count > 0:
        ship_counts[ship_name] = count

# Allow multiple of the same captain
captain_counts = {}
for captain_name in filtered_captains["Name"]:
    count = st.sidebar.number_input(
        f"{captain_name} (PV {filtered_captains[filtered_captains['Name'] == captain_name]['Cost'].values[0]})",
        0, 10, 0, key=f"captain_{captain_name}"
    )
    if count > 0:
        captain_counts[captain_name] = count

# Fighter creation method
fighter_method = st.sidebar.radio("Fighter Group Setup", ["Manual", "Auto by Points", "Random then Edit"])
group_type = st.sidebar.radio("Fighter Group Type", ["Flight", "Squadron"])
fighter_group_name = st.sidebar.text_input("Optional Name for Fighter Group")

# Pilot Experience Level
experience_level = st.sidebar.selectbox("Pilot Experience", ["Green", "Rookie", "Regular", "Veteran", "Elite"])
experience_cost_map = {
    "Green": 0,
    "Rookie": 4,
    "Regular": 8,
    "Veteran": 12,
    "Elite": 16
}

fighter_selections = []

if fighter_method == "Manual":
    for idx, row in filtered_fighters.iterrows():
        count = st.sidebar.number_input(
            f"{row['Fighter']} (PV {row['COST']})", 0, 10, 0, key=f"manual_{row['Fighter']}"
        )
        if count > 0:
            fighter_selections.extend([row["Fighter"]] * count)
elif fighter_method == "Auto by Points":
    max_points = st.sidebar.number_input("Max Points for Fighters", 0, 100, 10)
    total = 0
    while total < max_points:
        row = filtered_fighters.sample(1).iloc[0]
        if total + row["COST"] <= max_points:
            fighter_selections.append(row["Fighter"])
            total += row["COST"]
elif fighter_method == "Random then Edit":
    size = 4 if group_type == "Flight" else 12
    for i in range(size):
        row = filtered_fighters.sample(1, replace=True).iloc[0]
        default_count = st.sidebar.number_input(
            f"{row['Fighter']} (PV {row['COST']})", 0, 12, 1, key=f"random_{i}_{row['Fighter']}_{i}"
        )
        fighter_selections.extend([row["Fighter"]] * default_count)

# Function to round up
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
            per_flight = int(len(fighter_names) / 3)
            if per_flight == 0:
                return round_up(expanded[col].sum() / expanded["count"].sum())
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
            return round_up(sum(flight_averages) / 3)

    man = compute_stat("MAN")
    defense = compute_stat("DEF")
    intercept = compute_stat("INT")
    strafe = compute_stat("STR")

    ordnance = round_up(expanded["ORD"].sum())
    qualities = ", ".join(sorted(set(q for q in expanded["Qualities"].dropna())))
    base_cost = round_up(expanded["COST"].sum())
    pilot_experience_cost = experience_cost_map[experience_level]
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

# Store fighter groups in session state
if "fighter_groups" not in st.session_state:
    st.session_state.fighter_groups = []

# Add fighter group button
if fighter_selections and st.sidebar.button("Add Fighter Group to Force"):
    fighter_group = generate_fighter_group(fighter_selections, group_type=group_type)
    st.session_state.fighter_groups.append(fighter_group)

# Display fighter groups with removal option
remaining_groups = []
st.subheader("Fighter Groups")
for i, group in enumerate(st.session_state.fighter_groups):
    col1, col2 = st.columns([4, 1])
    with col1:
        st.markdown(f"**{group['Name']}** - {group['Type']} - {group['Experience']} - PV: {group['PV']}")
        st.text(f"{group['Fighters']}")
    with col2:
        if not st.checkbox("Remove", key=f"remove_fighter_{i}"):
            remaining_groups.append(group)

st.session_state.fighter_groups = remaining_groups

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

for group in st.session_state.fighter_groups:
    force.append(group)
    total_pv += group["PV"]

# Main output
st.subheader("Current Force")
st.write(pd.DataFrame(force))
st.markdown(f"**Total PV: {total_pv}**")

# Export
st.download_button("Download JSON", data=json.dumps(force, indent=2), file_name="force.json")
st.download_button("Download CSV", data=pd.DataFrame(force).to_csv(index=False), file_name="force.csv")

