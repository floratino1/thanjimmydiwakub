import streamlit as st
import streamlit.components.v1 as components
import json
import os
import time
import requests
from datetime import datetime

# 1. ตั้งค่าหน้าจอ
st.set_page_config(page_title="MT5 Professional Terminal", layout="wide", initial_sidebar_state="collapsed")

# ================= ระบบฐานข้อมูลผู้ใช้ =================
USER_FILE = "trading_users.json"

def load_users():
    if os.path.exists(USER_FILE):
        try:
            with open(USER_FILE, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return {"admin": "1234"}
    return {"admin": "1234"}

def save_users(users_dict):
    with open(USER_FILE, "w") as f:
        json.dump(users_dict, f, indent=4)

# ================= ฟังก์ชันดึงราคา (แก้ไข Exception ให้แคบลง) =================
def get_live_price(symbol):
    try:
        mapping = {
            "OANDA:XAUUSD": "PAXGUSDT",
            "BINANCE:BTCUSDT": "BTCUSDT",
            "BINANCE:ETHUSDT": "ETHUSDT",
            "BINANCE:SOLUSDT": "SOLUSDT",
            "FX:EURUSD": "EURUSDT",
            "FX:GBPUSD": "GBPUSDT",
            "FX:USDJPY": "JPYUSDT"
        }
        api_sym = mapping.get(symbol, "BTCUSDT")
        url = f"https://api.binance.com/api/v3/ticker/price?symbol={api_sym}"
        res = requests.get(url, timeout=5)
        res.raise_for_status()
        return float(res.json()['price'])
    except (requests.RequestException, KeyError, ValueError):
        return 0.0

# ================= CSS ธีม Dark Gold =================
st.markdown("""
<style>
    [data-testid="stAppViewContainer"] {
        background-color: #050505 !important;
        background-image: radial-gradient(circle at 50% 40%, #2b2000 0%, #050505 60%);
    }
    button[kind="primary"] {
        background: linear-gradient(135deg, #BF953F, #FCF6BA, #B38728, #FBF5B7, #AA771C) !important;
        color: black !important;
        font-weight: bold !important;
        border: none !important;
        border-radius: 30px !important;
    }
    .gold-text { color: #f5c542 !important; font-weight: bold; font-size: 18px; }
    .terminal-box {
        background-color: #000;
        border: 1px solid #222;
        padding: 15px;
        font-family: 'Consolas', monospace;
        color: #00ff00;
        border-radius: 5px;
    }
    .history-table {
        width: 100%;
        border-collapse: collapse;
        color: #ddd;
        font-size: 14px;
        margin-bottom: 20px;
    }
    .history-table th { color: #f5c542; border-bottom: 1px solid #333; padding: 10px; text-align: left; }
    .history-table td { padding: 8px; border-bottom: 1px solid #222; }
</style>
""", unsafe_allow_html=True)

# Session State Initialization
for key, default in {
    "logged_in": False, "show_register": False, "balance": 10000.0,
    "position": "None", "current_pnl": 0.0, "tp_price": 0.0,
    "sl_price": 0.0, "trade_history": [], "transactions": [],
    "entry_price": 0.0, "active_lot": 0.0, "active_asset": ""
}.items():
    if key not in st.session_state:
        st.session_state[key] = default

# ฟังก์ชันบันทึกประวัติ (แก้ไข Shadowing)
def add_to_history(h_asset, h_side, h_entry, h_exit, h_lot, h_pnl):
    record = {
        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "asset": h_asset, "side": h_side, "entry": h_entry,
        "exit": h_exit, "lot": h_lot, "pnl": h_pnl
    }
    st.session_state["trade_history"].insert(0, record)

def add_transaction(t_type, t_amt):
    transaction_record = {
        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "type": t_type, "amount": t_amt, "balance": st.session_state["balance"]
    }
    st.session_state["transactions"].insert(0, transaction_record)

# ================= 🛡️ ระบบเข้าสู่ระบบ =================
if not st.session_state["logged_in"]:
    st.markdown("<br><br><br>", unsafe_allow_html=True)
    _, col_auth, _ = st.columns([1, 1.2, 1])
    with col_auth:
        if not st.session_state["show_register"]:
            st.markdown("<h1 style='text-align: center; color: #FFDF00;'>✨ XAUUSD EXCLUSIVE</h1>", unsafe_allow_html=True)
            u_in = st.text_input("Username", placeholder="👤")
            p_in = st.text_input("Password", type="password", placeholder="🔑")
            if st.button("AUTHORIZE ACCESS", type="primary", use_container_width=True):
                users = load_users()
                if u_in in users and users[u_in] == p_in:
                    st.session_state.update({"logged_in": True, "username": u_in})
                    st.rerun()
                else:
                    st.error("❌ Invalid Credentials")
            if st.button("CREATE NEW ACCOUNT", use_container_width=True):
                st.session_state["show_register"] = True
                st.rerun()
        else:
            st.markdown("<h2 style='text-align: center; color: #FFDF00;'>📝 REGISTER</h2>", unsafe_allow_html=True)
            new_u = st.text_input("New Username")
            new_p = st.text_input("New Password", type="password")
            conf_p = st.text_input("Confirm Password", type="password")
            if st.button("REGISTER NOW", type="primary", use_container_width=True):
                if new_p == conf_p and new_u:
                    users_data = load_users()
                    users_data[new_u] = new_p
                    save_users(users_data)
                    st.success("✅ Account Created!")
                    st.session_state["show_register"] = False
                    time.sleep(1)
                    st.rerun()

# ================= 📈 Terminal Execution =================
else:
    head1, head2 = st.columns([8, 2])
    with head1:
        st.markdown(f"<h3 style='color:#FFDF00;'>⚜️ Terminal | <span style='color:white; font-size:16px;'>User: {st.session_state['username'].upper()}</span></h3>", unsafe_allow_html=True)
    if head2.button("🚪 Logout", use_container_width=True):
        st.session_state["logged_in"] = False
        st.rerun()

    assets = {
        "🥇 GOLD (XAUUSD)": "OANDA:XAUUSD",
        "₿ Bitcoin (BTC)": "BINANCE:BTCUSDT",
        "💎 Ethereum (ETH)": "BINANCE:ETHUSDT",
        "🇪🇺 EUR/USD": "FX:EURUSD"
    }

    if "selected_asset" not in st.session_state:
        st.session_state["selected_asset"] = "🥇 GOLD (XAUUSD)"

    curr_sym = assets[st.session_state["selected_asset"]]

    # เส้น Order
    order_script = ""
    if st.session_state["position"] != "None":
        order_script = f', "overlays": [{{"symbol": "{curr_sym}", "price": {st.session_state["entry_price"]}, "displayLabel": "ENTRY {st.session_state["position"]}", "color": "#BF953F"}}]'

    components.html(f"""
        <div id="tv_chart" style="height: 400px;"></div>
        <script src="https://s3.tradingview.com/tv.js"></script>
        <script>
        new TradingView.widget({{
            "autosize": true, "symbol": "{curr_sym}", "interval": "1", "theme": "dark", "container_id": "tv_chart", "hide_side_toolbar": false {order_script}
        }});
        </script>
    """, height=400)

    st.write("---")
    c1, c2, c3, c4 = st.columns([2, 1.5, 2.5, 4])

    with c1:
        st.markdown("<div class='gold-text'>📋 Market Watch</div>", unsafe_allow_html=True)
        st.session_state["selected_asset"] = st.selectbox("Asset", list(assets.keys()), label_visibility="collapsed")

    with c2:
        st.markdown("<div class='gold-text'>⚡ Volume</div>", unsafe_allow_html=True)
        lot = st.number_input("Lots", value=1.00, step=0.1)
        tp = st.number_input("TP", value=0.0, step=0.1)
        sl = st.number_input("SL", value=0.0, step=0.1)

    with c3:
        st.markdown("<div class='gold-text'>🚀 Execution</div>", unsafe_allow_html=True)
        if st.button("BUY", use_container_width=True):
            price = get_live_price(curr_sym)
            st.session_state.update({"position": "BUY", "active_asset": curr_sym, "entry_price": price, "tp_price": tp, "sl_price": sl, "active_lot": lot})
            st.rerun()
        if st.button("SELL", use_container_width=True):
            price = get_live_price(curr_sym)
            st.session_state.update({"position": "SELL", "active_asset": curr_sym, "entry_price": price, "tp_price": tp, "sl_price": sl, "active_lot": lot})
            st.rerun()
        if st.button("❌ CLOSE ALL", use_container_width=True) and st.session_state["position"] != "None":
            now_p = get_live_price(st.session_state["active_asset"])
            add_to_history(st.session_state["active_asset"], st.session_state["position"], st.session_state["entry_price"], now_p, st.session_state["active_lot"], st.session_state["current_pnl"])
            st.session_state["balance"] += st.session_state["current_pnl"]
            st.session_state["position"] = "None"
            st.rerun()

    with c4:
        st.markdown("<div class='gold-text'>💻 Terminal</div>", unsafe_allow_html=True)
        if st.session_state["position"] != "None":
            now_p = get_live_price(st.session_state["active_asset"])
            diff = (now_p - st.session_state["entry_price"]) if st.session_state["position"] == "BUY" else (st.session_state["entry_price"] - now_p)
            pnl = diff * st.session_state["active_lot"] * 100
            st.session_state["current_pnl"] = pnl

            # แก้ Simplify chained comparison
            tp_at, sl_at = st.session_state["tp_price"], st.session_state["sl_price"]
            triggered = False
            if st.session_state["position"] == "BUY":
                if (tp_at > 0 and now_p >= tp_at) or (sl_at > 0 and now_p <= sl_at): triggered = True
            else:
                if (tp_at > 0 and now_p <= tp_at) or (sl_at > 0 and now_p >= sl_at): triggered = True

            if triggered:
                add_to_history(st.session_state["active_asset"], st.session_state["position"], st.session_state["entry_price"], now_p, st.session_state["active_lot"], pnl)
                st.session_state["balance"] += pnl
                st.session_state["position"] = "None"
                st.rerun()

            pnl_col = "#00ff88" if pnl >= 0 else "#ff4d4d"
            st.markdown(f"""
            <div class="terminal-box">
                POS: <b style="color:{pnl_col}">{st.session_state['position']}</b> | LOT: {st.session_state['active_lot']:.2f}<br>
                ENTRY: {st.session_state['entry_price']:,.2f} | LIVE: {now_p:,.2f}<br>
                PNL: <span style="color:{pnl_col}; font-weight:bold;">${pnl:,.2f}</span>
            </div>
            """, unsafe_allow_html=True)
            time.sleep(2)
            st.rerun()
        else:
            st.markdown(f"<div class='terminal-box'>Balance: <span style='color:#00ff88;'>${st.session_state['balance']:,.2f}</span></div>", unsafe_allow_html=True)
            amt = st.number_input("Amount", min_value=0.0, value=100.0, step=10.0, key="cash_in", label_visibility="collapsed")
            d_c, w_c = st.columns(2)
            if d_c.button("➕ DEP", use_container_width=True):
                st.session_state["balance"] += amt
                add_transaction("DEPOSIT", amt); st.rerun()
            if w_c.button("➖ WIT", use_container_width=True) and amt <= st.session_state["balance"]:
                st.session_state["balance"] -= amt
                add_transaction("WITHDRAW", amt); st.rerun()

    # Histories
    st.write("---")
    h1, h2 = st.columns(2)
    with h1:
        st.markdown("<div class='gold-text'>📜 Trade History</div>", unsafe_allow_html=True)
        if st.session_state["trade_history"]:
            tbl = "<table class='history-table'><tr><th>Time</th><th>Asset</th><th>PnL</th></tr>"
            for t in st.session_state["trade_history"][:5]:
                col = '#00ff88' if t['pnl'] >= 0 else '#ff4d4d'
                tbl += f"<tr><td>{t['time'][-8:]}</td><td>{t['asset']}</td><td style='color:{col}'>${t['pnl']:,.2f}</td></tr>"
            st.markdown(tbl + "</table>", unsafe_allow_html=True)
    with h2:
        st.markdown("<div class='gold-text'>💳 Cashflow History</div>", unsafe_allow_html=True)
        if st.session_state["transactions"]:
            ctx = "<table class='history-table'><tr><th>Time</th><th>Type</th><th>Amount</th></tr>"
            for tx in st.session_state["transactions"][:5]:
                col = "#00ff88" if tx['type'] == "DEPOSIT" else "#ff4d4d"
                ctx += f"<tr><td>{tx['time'][-8:]}</td><td style='color:{col}'>{tx['type']}</td><td>${tx['amount']:,.2f}</td></tr>"
            st.markdown(ctx + "</table>", unsafe_allow_html=True)