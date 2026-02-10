"""
VVS Invoice Generator - Streamlit App
Simple invoice creation tool for contractors using Supabase catalog
"""

import streamlit as st
import pandas as pd
from supabase import create_client
from datetime import date
import io

# ============================================
# CONFIGURATION
# ============================================

# TODO: Replace with your actual Supabase credentials
SUPABASE_URL = "https://yejigzlrwhnrwgqcpwiz.supabase.co"
SUPABASE_KEY = "sb_publishable_NOw_65NMJiUjNlGIdpK38w_x2w_3BSe"

# Initialize Supabase client
@st.cache_resource
def init_supabase():
    return create_client(SUPABASE_URL, SUPABASE_KEY)

supabase = init_supabase()

# ============================================
# SESSION STATE
# ============================================

if 'invoice_items' not in st.session_state:
    st.session_state.invoice_items = []

# ============================================
# HELPER FUNCTIONS
# ============================================

def search_items(query):
    """Search catalog by item number, description, or category"""
    if not query:
        # Return all items if no query
        response = supabase.table('invoice_master').select('*').limit(50).execute()
    else:
        # Simple search - get all and filter in Python
        response = supabase.table('invoice_master').select('*').execute()
        
        # Filter results that contain the query (case insensitive)
        query_lower = query.lower()
        filtered = [
            item for item in response.data 
            if query_lower in (item.get('item') or '').lower()
            or query_lower in (item.get('item_no') or '').lower()
            or query_lower in (item.get('category') or '').lower()
        ]
        
        return filtered
    
    return response.data

def add_to_invoice(item, quantity):
    """Add item to invoice with quantity"""
    invoice_item = {
        'item_no': item['item_no'],
        'beskrivning': item['item'],
        'kategori': item['category'],
        'antal': quantity,
        'enhet': item['unit'],
        'pris_per_enhet': float(item['price']) if item['price'] else 0.0,
        'summa': quantity * (float(item['price']) if item['price'] else 0.0)
    }
    st.session_state.invoice_items.append(invoice_item)

def calculate_rot_deduction(labor_cost_with_moms, rot_percentage=30):
    """Calculate ROT tax deduction (30% of labor cost including moms)"""
    return labor_cost_with_moms * (rot_percentage / 100)

def generate_invoice_text(customer_name, project_number):
    """Generate plain text invoice"""
    lines = []
    lines.append(f"FAKTURA")
    lines.append(f"=" * 80)
    lines.append(f"Kund: {customer_name}")
    lines.append(f"Projekt: {project_number}")
    lines.append(f"Datum: {date.today().strftime('%Y-%m-%d')}")
    lines.append(f"")
    lines.append(f"{'Pos':<4} {'Art.nr':<12} {'Beskrivning':<25} {'Antal':>6} {'Enhet':<8} {'A-pris':>10} {'Belopp':>12} {'Inkl moms':>12}")
    lines.append("-" * 100)
    
    total_excl_moms = 0
    total_incl_moms = 0
    labor_total_incl_moms = 0
    pos = 1
    
    for item in st.session_state.invoice_items:
        art_no = item['item_no'] or ''
        belopp_excl_moms = item['summa']
        belopp_incl_moms = belopp_excl_moms * 1.25  # Add 25% moms to everything
        
        lines.append(
            f"{pos:<4} {art_no:<12} {item['beskrivning'][:25]:<25} "
            f"{item['antal']:>6.2f} {item['enhet']:<8} "
            f"{item['pris_per_enhet']:>10.2f} {belopp_excl_moms:>12.2f} {belopp_incl_moms:>12.2f}"
        )
        
        total_excl_moms += belopp_excl_moms
        total_incl_moms += belopp_incl_moms
        
        # Track labor (ARBETE) for ROT deduction - calculated on amount WITH moms
        if item['kategori'] == 'ARBETE':
            labor_total_incl_moms += belopp_incl_moms
        
        pos += 1
    
    lines.append("-" * 100)
    lines.append(f"{'TOTAL EXKL MOMS:':>70} {total_excl_moms:>12.2f} kr")
    lines.append(f"{'TOTAL INKL MOMS (25%):':>70} {total_incl_moms:>12.2f} kr")
    
    # ROT deduction (only on ARBETE items, calculated from moms-included amount)
    if labor_total_incl_moms > 0:
        rot_deduction = calculate_rot_deduction(labor_total_incl_moms)
        lines.append(f"")
        lines.append(f"{'ROT-AVDRAG (30% av arbetskostnad inkl moms):':>70} {-rot_deduction:>12.2f} kr")
        lines.append(f"{'FAKTURA TOTAL:':>70} {total_incl_moms - rot_deduction:>12.2f} kr")
    else:
        lines.append(f"")
        lines.append(f"{'FAKTURA TOTAL:':>70} {total_incl_moms:>12.2f} kr")
    
    return "\n".join(lines)

# ============================================
# STREAMLIT UI
# ============================================

st.set_page_config(page_title="VVS Faktura", page_icon="🔧", layout="wide")

st.title("🔧 VVS Fakturaverktyg")
st.markdown("*Enkel fakturahantering för VVS-installatörer*")

# Sidebar - Invoice Info
with st.sidebar:
    st.header("📋 Fakturainformation")
    customer_name = st.text_input("Kundnamn", placeholder="Ex: Andersson Bygg AB")
    project_number = st.text_input("Projektnummer", placeholder="Ex: P2024-001")
    
    st.divider()
    
    st.header("📊 Faktura")
    if st.session_state.invoice_items:
        total_excl_moms = sum(item['summa'] for item in st.session_state.invoice_items)
        total_incl_moms = total_excl_moms * 1.25
        labor_total_incl_moms = sum(item['summa'] * 1.25 for item in st.session_state.invoice_items if item['kategori'] == 'ARBETE')
        rot_deduction = calculate_rot_deduction(labor_total_incl_moms)
        
        st.metric("Total exkl moms", f"{total_excl_moms:.2f} kr")
        st.metric("Total inkl moms", f"{total_incl_moms:.2f} kr")
        if labor_total_incl_moms > 0:
            st.metric("ROT-avdrag (30%)", f"{rot_deduction:.2f} kr")
            st.metric("Att betala", f"{total_incl_moms - rot_deduction:.2f} kr")
        else:
            st.metric("Att betala", f"{total_incl_moms:.2f} kr")
        
        if st.button("🗑️ Rensa faktura", width='stretch'):
            st.session_state.invoice_items = []
            st.rerun()
    else:
        st.info("Ingen faktura skapad än")

# Main area - two columns
col1, col2 = st.columns([1, 1])

# Left column - Search and Add Items
with col1:
    st.header("🔍 Sök artiklar")
    
    search_query = st.text_input(
        "Sök efter artikel, beskrivning eller kategori",
        placeholder="Ex: grenuttag, 2405276, ARBETE"
    )
    
    # Auto-search when query changes or on button click
    results = search_items(search_query) if search_query or st.session_state.get('show_all', False) else []
    
    if st.button("Visa alla artiklar", width='stretch'):
        st.session_state['show_all'] = True
        results = search_items("")
    
    if results:
        st.success(f"Hittade {len(results)} artiklar")
        
        # Create a form for each item
        for idx, item in enumerate(results):
            with st.form(key=f"form_{item['item_no']}_{idx}"):
                st.subheader(f"{item['item']}")
                
                col_info, col_qty = st.columns([2, 1])
                
                with col_info:
                    st.write(f"**Art.nr:** {item['item_no'] or 'N/A'}")
                    st.write(f"**Kategori:** {item['category']}")
                    st.write(f"**Enhet:** {item['unit']}")
                    st.write(f"**Pris:** {item['price'] or 0} kr/{item['unit']}")
                
                with col_qty:
                    quantity = st.number_input(
                        "Antal",
                        min_value=0.1,
                        value=1.0,
                        step=0.5,
                        key=f"qty_{item['item_no']}_{idx}"
                    )
                
                if st.form_submit_button("➕ Lägg till", width='stretch'):
                    add_to_invoice(item, quantity)
                    st.success("✅ Tillagd!")
                
                st.divider()
    elif search_query:
        st.warning("Inga artiklar hittades")

# Right column - Current Invoice
with col2:
    st.header("📄 Aktuell faktura")
    
    if st.session_state.invoice_items:
        # Display items as dataframe
        df = pd.DataFrame(st.session_state.invoice_items)
        
        # Allow editing quantities
        st.dataframe(
            df[['item_no', 'beskrivning', 'antal', 'enhet', 'pris_per_enhet', 'summa']],
            width='stretch',
            hide_index=True
        )
        
        # Remove item buttons
        st.write("**Ta bort artikel:**")
        for idx, item in enumerate(st.session_state.invoice_items):
            col_x, col_y = st.columns([4, 1])
            with col_x:
                st.write(f"{item['beskrivning']}")
            with col_y:
                if st.button("🗑️", key=f"remove_{idx}"):
                    st.session_state.invoice_items.pop(idx)
                    st.rerun()
        
        st.divider()
        
        # Generate invoice
        if customer_name and project_number:
            if st.button("📥 Generera faktura", width='stretch', type="primary"):
                invoice_text = generate_invoice_text(customer_name, project_number)
                
                # Display preview
                st.text_area("Förhandsvisning", invoice_text, height=400)
                
                # Download button
                st.download_button(
                    label="💾 Ladda ner faktura (TXT)",
                    data=invoice_text,
                    file_name=f"faktura_{project_number}_{date.today()}.txt",
                    mime="text/plain"
                )
        else:
            st.warning("⚠️ Fyll i kundnamn och projektnummer för att generera faktura")
    else:
        st.info("Lägg till artiklar från sökningen till vänster")

# Footer
st.divider()
st.caption("VVS Fakturaverktyg v1.0 | Powered by Supabase + Streamlit")