import streamlit as st
import pandas as pd
import random
import json
import math

@st.cache_data
def load_data():
    ships = pd.read_csv("ships.csv")
    captains = pd.read_csv("captains.csv")
    fighters = pd.read_csv("fighters.csv")
    premade_fighters = pd.read_csv("Premade_fighters.csv")

    # Strip whitespace from column names and 'Faction' values
    for df in [ships, captains, fighters, premade_fighters]:
        df.columns = df.columns.str.strip()
        if "Faction" in df.columns:
            df["Faction"] = df["Faction"].str.strip()

    return ships, captains, fighters, premade_fighters

ships_df, captains_df, fighters_df, premade_df = load_data()

st.title("Aetherstream: Leviathan Army Builder")

st.markdown(
    "[📘 How to Use This App](https://github.com/jpbell27/leviathan-army-builder/blob/main/README.md)",
    unsafe_allow_html=True
)

st.sidebar.header("Build Your Force")
faction = st.sidebar.selectbox("Select Faction", ships_df["Faction"].unique())

@st.cache_data
def filter_by_faction(faction, ships_df, captains_df, fighters_df, premade_df):
    return (
        ships_df[ships_df["Faction"] == faction],
        captains_df[captains_df["Faction"] == faction],
        fighters_df[fighters_df["Faction"] == faction],
        premade_df[premade_df["Faction"] == faction]
    )

with st.sidebar.expander("⚙️ Configure Your Force", expanded=False):
    filtered_ships, filtered_captains, filtered_fighters, filtered_premade = filter_by_faction(
        faction, ships_df, captains_df, fighters_df, premade_df
    )

    # Ship selection
    st.subheader("Ships")
    ship_counts = {}
    for ship_name in filtered_ships["Ship Name"]:
        count = st.number_input(
            f"{ship_name} (PV {filtered_ships[filtered_ships['Ship Name'] == ship_name]['Cost'].values[0]})",
            0, 10, 0, key=f"ship_{ship_name}")
        if count > 0:
            ship_counts[ship_name] = count

    # Captain selection
    st.subheader("Captains")
    captain_counts = {}
    for captain_name in filtered_captains["Name"]:
        count = st.number_input(
            f"{captain_name} (PV {filtered_captains[filtered_captains['Name'] == captain_name]['Cost'].values[0]})",
            0, 10, 0, key=f"captain_{captain_name}")
        if count > 0:
            captain_counts[captain_name] = count

    # Pre-made Fighter Groups
    st.subheader("Pre-made Fighter Groups")
    selected_premade = {}
    if not filtered_premade.empty:
        for i, row in filtered_premade.iterrows():
            group_name = row["Name"]
            group_strength = row["Strength"]
            group_points = row["Points"]
            selected = st.checkbox(f"{group_name} ({group_strength}, PV {group_points})", key=f"premade_{group_name}_{i}")
            if selected:
                carrier = st.selectbox(f"Assign '{group_name}' to Carrier", options=list(ship_counts.keys()) or ["Unassigned"], key=f"carrier_{group_name}_{i}")
                selected_premade[group_name] = {
                    "Strength": group_strength,
                    "PV": group_points,
                    "Carrier": carrier
                }
    
    round_up = lambda x: math.ceil(x)
    
    # Fighter group generator
    def generate_fighter_group(fighter_names, group_type, assigned_ship, fighter_group_name, experience_level, filtered_fighters, experience_cost_map):
        subset = filtered_fighters[filtered_fighters["Fighter"].isin(fighter_names)]
        counts = pd.Series(fighter_names).value_counts()
    
        expanded = pd.concat([
            subset[subset["Fighter"] == name].iloc[[0]].copy().assign(count=int(count))
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
        ordnance = int((expanded["ORD"] * expanded["count"]).sum())
    
        qualities = ", ".join(sorted(set(q for q in expanded["Qualities"].dropna())))
        base_cost = float((expanded["COST"] * expanded["count"]).sum())
        pilot_experience_cost = experience_cost_map[experience_level] * int(expanded["count"].sum())
        total_cost = round_up(base_cost + pilot_experience_cost)
    
        return {
            "Type": group_type,
            "Name": fighter_group_name if fighter_group_name else f"{group_type} Group",
            "Fighters": fighter_names,
            "MAN": int(man),
            "DEF": int(defense),
            "INT": int(intercept),
            "STR": int(strafe),
            "ORD": ordnance,
            "Qualities": qualities,
            "Experience": experience_level,
            "PV": total_cost,
            "Assigned Ship": assigned_ship
        }
    
    # Fighter creation
    st.sidebar.markdown("---")
    
    with st.sidebar.expander("🛠 Fighter Group Creator", expanded=False):
        fighter_method = st.radio("Fighter Group Setup", ["Manual", "Auto by Points", "Random then Edit", "Optimize by Stat"])
        group_type = st.radio("Fighter Group Type", ["Flight", "Squadron"])
        fighter_group_name = st.text_input("Optional Name for Fighter Group")
        experience_level = st.selectbox("Pilot Experience", ["Green", "Rookie", "Regular", "Veteran", "Elite"])
        experience_cost_map = {
            "Green": 0, "Rookie": 1, "Regular": 2, "Veteran": 3, "Elite": 4
        }
    
        if "fighter_groups" not in st.session_state:
            st.session_state.fighter_groups = []
    
        fighter_selections = []
    
        if fighter_method == "Manual":
            max_size = 4 if group_type == "Flight" else 12
            current_total = 0
            for idx, row in filtered_fighters.iterrows():
                remaining = max_size - current_total
                if remaining <= 0:
                    break
                count = st.number_input(f"{row['Fighter']} (PV {row['COST']})", 0, remaining, 0, key=f"manual_{row['Fighter']}")
                if count > 0:
                    fighter_selections.extend([row["Fighter"]] * count)
                    current_total += count
    
        elif fighter_method == "Auto by Points":
            max_points = st.number_input("Max Points for Fighters", min_value=1, max_value=100, value=10)
            size_limit = 4 if group_type == "Flight" else 12
            pilot_cost = experience_cost_map[experience_level]
            total_cost = 0
            shuffled_fighters = filtered_fighters.sample(frac=1).reset_index(drop=True)
    
            for _, row in shuffled_fighters.iterrows():
                total = row["COST"] + pilot_cost
                if (total_cost + total <= max_points) and len(fighter_selections) < size_limit:
                    fighter_selections.append(row["Fighter"])
                    total_cost += total
    
            st.markdown(f"Selected fighters cost: **{total_cost} / {max_points}** PV")
    
        elif fighter_method == "Random then Edit":
            size = 4 if group_type == "Flight" else 12
            for i in range(size):
                row = filtered_fighters.sample(1).iloc[0]
                count = st.number_input(f"{row['Fighter']} (PV {row['COST']})", 0, size, 1, key=f"random_{i}_{row['Fighter']}")
                fighter_selections.extend([row["Fighter"]] * count)
                if len(fighter_selections) >= size:
                    fighter_selections = fighter_selections[:size]
                    break


        elif fighter_method == "Optimize by Stat":
            optimize_stat = st.selectbox("Stat to Optimize", ["ORD", "MAN", "DEF", "INT", "STR"])
            max_points = st.number_input("Max Points for Fighters", min_value=1, max_value=100, value=10)
            size_limit = 4 if group_type == "Flight" else 12
            pilot_cost = experience_cost_map[experience_level]
        
            scored = []
            for _, row in filtered_fighters.iterrows():
                total_cost_per_fighter = row["COST"] + pilot_cost
                stat_value = row[optimize_stat]
                if total_cost_per_fighter > 0:
                    score = stat_value / total_cost_per_fighter
                    scored.append((score, row["Fighter"], total_cost_per_fighter))
        
            scored.sort(reverse=True)
        
            fighter_selections = []
            total_cost = 0
        
            for score, fighter_name, cost in scored:
                if len(fighter_selections) >= size_limit:
                    break
                if total_cost + cost <= max_points:
                    fighter_selections.append(fighter_name)
                    total_cost += cost
        
            if total_cost > max_points:
                st.warning(f"Warning: total PV {total_cost} exceeds the max {max_points}! Something may be wrong.")
        
            st.markdown(
                f"Selected fighters (optimized for **{optimize_stat}**) cost: **{total_cost} / {max_points}** PV"
            )
    
        # Assign fighter group to a ship
        available_ships = [name for name, count in ship_counts.items() for _ in range(count)]
        assigned_ship = st.selectbox("Assign this Fighter Group to a Ship", ["Unassigned"] + available_ships)
    
        if st.button("Add Fighter Group"):
            size = len(fighter_selections)
            if group_type == "Flight" and size != 4:
                st.error("A Flight must contain exactly 4 fighters.")
            elif group_type == "Squadron" and (size < 1 or size > 12):
                st.error("A Squadron must contain between 1 and 12 fighters.")
            else:
                new_group = generate_fighter_group(
                    fighter_selections, group_type, assigned_ship,
                    fighter_group_name, experience_level,
                    filtered_fighters, experience_cost_map
                )
                st.session_state.fighter_groups.append(new_group)
                st.success(f"{group_type} added!")

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

available_captains = [name for name, count in captain_counts.items() for _ in range(count)]

if "ship_captain_assignments" not in st.session_state:
    st.session_state.ship_captain_assignments = {}

st.subheader("Assign Captains to Ships")

for i, entry in enumerate(force):
    if entry["Type"] == "Ship":
        ship_name = entry["Ship Name"]
        key = f"assign_captain_{i}"
        selected = st.selectbox(f"Captain for {ship_name} #{i + 1}", ["None"] + available_captains, key=key)
        st.session_state.ship_captain_assignments[key] = {"ship": ship_name, "captain": selected}

# Show fighter groups with ship assignments
index_to_remove = None
for i, group in enumerate(st.session_state.fighter_groups):
    col1, col2 = st.columns([5, 1])
    with col1:
        st.markdown(f"**{group['Name']}** | Type: {group['Type']} | PV: {group['PV']}")
        st.markdown(f"Fighters: {', '.join(group['Fighters'])}")
        st.markdown(f"Stats – MAN: {group['MAN']}, DEF: {group['DEF']}, INT: {group['INT']}, STR: {group['STR']}, ORD: {group['ORD']}")
        st.markdown(f"Qualities: {group['Qualities']} | Experience: {group['Experience']}")
        st.markdown(f"🛡 Assigned Ship: {group['Assigned Ship']}")
    with col2:
        if st.button("Remove", key=f"remove_{i}"):
            index_to_remove = i
    st.markdown("---")

if index_to_remove is not None:
    st.session_state.fighter_groups.pop(index_to_remove)

# Final force
for group in st.session_state.fighter_groups:
    force.append(group)
    total_pv += group["PV"]

# Add pre-made fighter groups to force
for group_name, details in selected_premade.items():
    force.append({
        "Type": f"Pre-made {details['Strength']}",
        "Name": group_name,
        "Carrier": details["Carrier"],
        "PV": int(details["PV"])
    })
    total_pv += int(details["PV"])

# Attach captain assignments
for i, entry in enumerate(force):
    if entry["Type"] == "Ship":
        key = f"assign_captain_{i}"
        assignment = st.session_state.ship_captain_assignments.get(key)
        entry["Captain"] = assignment["captain"] if assignment and assignment["captain"] != "None" else "Unassigned"

# Final display
st.subheader("Current Force")
st.write(pd.DataFrame(force))
st.markdown(f"**Total PV: {total_pv}**")

# Export
serializable_force = [
    {k: (int(v) if isinstance(v, (int, float)) and not isinstance(v, bool) else v) for k, v in entry.items()}
    for entry in force
]

st.download_button("Download JSON", data=json.dumps(serializable_force, indent=2), file_name="force.json")
st.download_button("Download CSV", data=pd.DataFrame(serializable_force).to_csv(index=False), file_name="force.csv")

