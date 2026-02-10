# VVS Invoice App - Installation Guide

## Quick Start (5 minutes)

### 1. Install Python Requirements

```bash
pip install -r requirements.txt
```

### 2. Configure Supabase

Open `vvs_invoice_app.py` and replace these lines (around line 16-17):

```python
SUPABASE_URL = "YOUR_SUPABASE_URL"  # Replace with your actual URL
SUPABASE_KEY = "YOUR_SUPABASE_ANON_KEY"  # Replace with your actual key
```

**Where to find these:**
1. Go to your Supabase project
2. Click **Settings** (gear icon)
3. Click **API**
4. Copy:
   - **Project URL** → `SUPABASE_URL`
   - **anon public** key → `SUPABASE_KEY`

### 3. Run the App

```bash
streamlit run vvs_invoice_app.py
```

App opens in browser at: `http://localhost:8501`

---

## How to Use

### Search for Items
1. Type search query (product name, article number, or category)
2. Click "Sök"
3. Browse results

### Add to Invoice
1. Set quantity in the result
2. Click "➕ Lägg till"
3. Item appears in right panel

### Generate Invoice
1. Fill in customer name and project number (left sidebar)
2. Click "📥 Generera faktura"
3. Preview appears
4. Click "💾 Ladda ner faktura" to save as TXT file

### ROT Tax Deduction
- Automatically calculated for items in category "ARBETE"
- Shows 30% deduction on labor costs
- Final amount = Total - ROT deduction

---

## Features

✅ **Search catalog** - Find items by name, number, or category
✅ **Add items** - Set quantities, auto-calculates totals
✅ **ROT calculation** - Automatic tax deduction for labor
✅ **Generate invoice** - Plain text format, ready to print
✅ **Download** - Save as TXT file

---

## Folder Structure

```
vvs-invoice/
├── vvs_invoice_app.py      # Main Streamlit app
├── requirements.txt        # Python dependencies
└── README.md              # This file
```

---

## Next Steps (Optional Improvements)

### 1. Add PDF Export
```bash
pip install reportlab
```

Then modify `generate_invoice_text()` to create PDF instead of TXT.

### 2. Add Logo/Branding
- Upload company logo
- Customize colors in Streamlit config

### 3. Save Invoices to Database
- Create `invoices` table in Supabase
- Store generated invoices for history

### 4. Add Customer Database
- Create `customers` table
- Auto-fill customer info from dropdown

### 5. Deploy Online (Free)
- Deploy to Streamlit Cloud (free tier)
- Share link with employees
- Access from anywhere

---

## Troubleshooting

### "Connection Error" when searching
- Check your Supabase URL and key are correct
- Make sure your Supabase project is active
- Check internet connection

### "No items found"
- Verify your `items` table has data
- Check column names match: `item_no`, `item`, `category`, `unit`, `price_unit`
- Try searching with just one letter

### App won't start
- Make sure Python 3.9+ is installed
- Run: `pip install -r requirements.txt` again
- Check for error messages in terminal

---

## Support

Need help? Check:
- Streamlit docs: https://docs.streamlit.io
- Supabase docs: https://supabase.com/docs

---

**Version:** 1.0  
**Last Updated:** February 2026
