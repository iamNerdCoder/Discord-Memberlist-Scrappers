import pandas as pd

# --- CONFIGURATION ---
TARGET_FILE = 'name-of-file1.xlsx'
CROSS_REF_FILE = 'name-of-file2.xlsx'
OUTPUT_FILE = 'common_members.xlsx'

def cross_reference():
    print("[!] Loading files...")
    try:
        # We load 'User ID' as a string immediately to prevent any precision loss
        df_target = pd.read_excel(TARGET_FILE, dtype={'User ID': str})
        df_cross = pd.read_excel(CROSS_REF_FILE, dtype={'User ID': str})
    except FileNotFoundError as e:
        print(f"[ERROR] Could not find file: {e}")
        return

    print(f"[*] Target ({TARGET_FILE}) count: {len(df_target)}")
    print(f"[*] Cross-ref ({CROSS_REF_FILE}) count: {len(df_cross)}")

    # Standardize column names (optional, ensures no trailing spaces)
    df_target.columns = df_target.columns.str.strip()
    df_cross.columns = df_cross.columns.str.strip()

    # Find common members based on User ID
    common_mask = df_target['User ID'].isin(df_cross['User ID'])
    common_members = df_target[common_mask].copy()

    # Drop 'Role IDs' as requested
    if 'Role IDs' in common_members.columns:
        common_members.drop(columns=['Role IDs'], inplace=True)

    # Select final columns
    final_columns = ['Username', 'User ID', 'Type']
    existing_cols = [col for col in final_columns if col in common_members.columns]
    common_members = common_members[existing_cols]

    # Force User ID to string one last time before export
    common_members['User ID'] = common_members['User ID'].astype(str)

    # Save to Excel
    # Using the 'xlsxwriter' engine can help with specific formatting if needed
    common_members.to_excel(OUTPUT_FILE, index=False)
    
    print(f"[SUCCESS] Found {len(common_members)} common members.")
    print(f"[!] Results saved to: {OUTPUT_FILE}")

if __name__ == "__main__":
    cross_reference()