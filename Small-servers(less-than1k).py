import discum
import pandas as pd

# CONFIG
TOKEN = 'YOUR DISCORD TOKEN'
GUILD_ID = 'YOUR TARGET SERVER'
CHANNEL_ID = 'ANY OPEN CHANNEL' # Required for some member fetching methods

bot = discum.Client(token=TOKEN, build_num="351221")

ADMIN_ROLES = set()
STAFF_ROLES = set()
VC_MOD_ROLES = set()

def audit_roles(guild_id):
    roles = bot.gateway.session.guild(guild_id).roles
    for rid, info in roles.items():
        p = int(info.get('permissions', 0))
        # Admin: Administrator (0x8)
        if (p & 0x8) == 0x8:
            ADMIN_ROLES.add(rid)
        # Staff: Manage Msg (0x2000) or Kick (0x2) or Ban (0x4)
        elif (p & 0x2000) == 0x2000 or (p & 0x2) == 0x2 or (p & 0x4) == 0x4:
            STAFF_ROLES.add(rid)
        # VC Mod: Mute (0x400000) or Deafen (0x800000)
        elif (p & 0x400000) == 0x400000 or (p & 0x800000) == 0x800000:
            VC_MOD_ROLES.add(rid)

def get_member_type(info, roles):
    if info.get('bot'): return "Bot"
    if any(r in ADMIN_ROLES for r in roles): return "Admin"
    if any(r in STAFF_ROLES for r in roles): return "Staff"
    if any(r in VC_MOD_ROLES for r in roles): return "VC Mod"
    return "Regular Member"

def fetch_and_export(resp, guild_id):
    if bot.gateway.finishedMemberFetching(guild_id):
        # First, map the server roles
        audit_roles(guild_id)
        
        members_dict = bot.gateway.session.guild(guild_id).members
        print(f"\n[!] Total members captured: {len(members_dict)}")
        
        data = []
        for uid, info in members_dict.items():
            member_roles = info.get('roles', [])
            
            data.append({
                "Username": info.get('username'),
                "User ID": str(uid), # Force string to avoid E+18 format
                "Type": get_member_type(info, member_roles),
                "Role IDs": ",".join(member_roles)
            })
        
        # Save to Excel
        df = pd.DataFrame(data)
        df.to_excel("CHOOSE_A_NAME_FOR_THE_EXCEL.xlsx", index=False)
        print(f"Success: Found {len(ADMIN_ROLES)} Admin roles and {len(STAFF_ROLES)} Staff roles.")
        print("File saved to server_members_classified.xlsx")
        
        bot.gateway.close()

# Start
print("Initializing Classified Fetcher...")

bot.gateway.fetchMembers(GUILD_ID, CHANNEL_ID, keep="all", wait=1)
bot.gateway.command({'function': fetch_and_export, 'params': {'guild_id': GUILD_ID}})
bot.gateway.run()

input("\nProcess finished. Press Enter to exit...")