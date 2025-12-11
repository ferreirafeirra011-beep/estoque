# estoque_pro.py
import sqlite3
from tkinter import *
from tkinter import messagebox, ttk, filedialog
from datetime import datetime
from fpdf import FPDF
import os

DB_NAME = "estoque.db"

# ------------------ BANCO DE DADOS ------------------
conn = sqlite3.connect(DB_NAME)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS produtos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT NOT NULL,
    quantidade INTEGER NOT NULL,
    preco REAL NOT NULL
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS vendas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    produto_id INTEGER,
    produto_nome TEXT,
    quantidade INTEGER,
    preco_unitario REAL,
    total REAL,
    data_hora TEXT
)
""")

conn.commit()

# ------------------ FUNÇÕES PRODUTOS ------------------
def listar_produtos():
    for row in tree_produtos.get_children():
        tree_produtos.delete(row)
    cursor.execute("SELECT id, nome, quantidade, preco FROM produtos ORDER BY nome")
    for prod in cursor.fetchall():
        tree_produtos.insert("", END, values=prod)

def limpar_campos_produto():
    entry_nome.delete(0, END)
    entry_qtd.delete(0, END)
    entry_preco.delete(0, END)

def adicionar_produto():
    nome = entry_nome.get().strip()
    try:
        quantidade = int(entry_qtd.get())
        preco = float(entry_preco.get())
    except:
        messagebox.showerror("Erro", "Quantidade deve ser inteiro e preço número (use ponto).")
        return
    if not nome:
        messagebox.showerror("Erro", "Nome é obrigatório.")
        return
    cursor.execute("INSERT INTO produtos (nome, quantidade, preco) VALUES (?, ?, ?)",
                   (nome, quantidade, preco))
    conn.commit()
    listar_produtos()
    limpar_campos_produto()
    messagebox.showinfo("Sucesso", "Produto adicionado.")

def selecionar_produto(event):
    selected = tree_produtos.selection()
    if not selected: return
    item = tree_produtos.item(selected[0])['values']
    entry_nome.delete(0, END); entry_nome.insert(0, item[1])
    entry_qtd.delete(0, END); entry_qtd.insert(0, item[2])
    entry_preco.delete(0, END); entry_preco.insert(0, item[3])

def editar_produto():
    selected = tree_produtos.selection()
    if not selected:
        messagebox.showerror("Erro", "Selecione um produto para editar.")
        return
    item = tree_produtos.item(selected[0])['values']
    prod_id = item[0]
    nome = entry_nome.get().strip()
    try:
        quantidade = int(entry_qtd.get())
        preco = float(entry_preco.get())
    except:
        messagebox.showerror("Erro", "Quantidade deve ser inteiro e preço número.")
        return
    if not nome:
        messagebox.showerror("Erro", "Nome é obrigatório.")
        return
    cursor.execute("UPDATE produtos SET nome=?, quantidade=?, preco=? WHERE id=?",
                   (nome, quantidade, preco, prod_id))
    conn.commit()
    listar_produtos()
    limpar_campos_produto()
    messagebox.showinfo("Sucesso", "Produto atualizado.")

def excluir_produto():
    selected = tree_produtos.selection()
    if not selected:
        messagebox.showerror("Erro", "Selecione um produto para excluir.")
        return
    item = tree_produtos.item(selected[0])['values']
    prod_id = item[0]
    if messagebox.askyesno("Confirmar", f"Excluir produto '{item[1]}'?"):
        cursor.execute("DELETE FROM produtos WHERE id=?", (prod_id,))
        conn.commit()
        listar_produtos()
        limpar_campos_produto()
        messagebox.showinfo("Sucesso", "Produto excluído.")

# ------------------ FUNÇÕES VENDAS ------------------
def listar_vendas():
    for row in tree_vendas.get_children():
        tree_vendas.delete(row)
    cursor.execute("SELECT id, produto_nome, quantidade, preco_unitario, total, data_hora FROM vendas ORDER BY data_hora DESC")
    for v in cursor.fetchall():
        tree_vendas.insert("", END, values=v)

def limpar_campos_venda():
    combo_venda_produto.set('')
    entry_venda_qtd.delete(0, END)

def carregar_produtos_no_combo():
    cursor.execute("SELECT id, nome, quantidade, preco FROM produtos ORDER BY nome")
    prods = cursor.fetchall()
    combo_venda_produto['values'] = [f"{p[0]} - {p[1]} (qtd: {p[2]})" for p in prods]

def realizar_venda():
    sel = combo_venda_produto.get().strip()
    if not sel:
        messagebox.showerror("Erro", "Selecione um produto.")
        return
    try:
        qtd_venda = int(entry_venda_qtd.get())
        if qtd_venda <= 0:
            raise ValueError
    except:
        messagebox.showerror("Erro", "Quantidade de venda inválida.")
        return
    prod_id = int(sel.split(" - ")[0])
    cursor.execute("SELECT nome, quantidade, preco FROM produtos WHERE id=?", (prod_id,))
    row = cursor.fetchone()
    if not row:
        messagebox.showerror("Erro", "Produto não encontrado.")
        return
    nome, estoque, preco_unit = row
    if qtd_venda > estoque:
        messagebox.showerror("Erro", f"Estoque insuficiente (tem {estoque}).")
        return
    total = round(preco_unit * qtd_venda, 2)
    data_hora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("INSERT INTO vendas (produto_id, produto_nome, quantidade, preco_unitario, total, data_hora) VALUES (?, ?, ?, ?, ?, ?)",
                   (prod_id, nome, qtd_venda, preco_unit, total, data_hora))
    cursor.execute("UPDATE produtos SET quantidade = quantidade - ? WHERE id=?", (qtd_venda, prod_id))
    conn.commit()
    carregar_produtos_no_combo()
    listar_produtos()
    listar_vendas()
    limpar_campos_venda()
    messagebox.showinfo("Sucesso", f"Venda registrada. Total: R$ {total:.2f}")

# ------------------ RELATÓRIO PDF ------------------
def gerar_relatorio_pdf():
    # Perguntar local para salvar
    default_name = f"relatorio_estoque_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf"
    filepath = filedialog.asksaveasfilename(defaultextension=".pdf", initialfile=default_name,
                                            filetypes=[("PDF files", "*.pdf")])
    if not filepath:
        return
    # Buscar dados
    cursor.execute("SELECT id, nome, quantidade, preco FROM produtos ORDER BY nome")
    produtos = cursor.fetchall()
    cursor.execute("SELECT id, produto_nome, quantidade, preco_unitario, total, data_hora FROM vendas ORDER BY data_hora DESC")
    vendas = cursor.fetchall()

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, "Relatório de Estoque e Vendas", ln=True, align="C")
    pdf.ln(6)
    pdf.set_font("Arial", size=12)
    pdf.cell(0, 8, f"Gerado em: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", ln=True)
    pdf.ln(6)

    # Inventário
    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 8, "Inventário", ln=True)
    pdf.ln(2)
    pdf.set_font("Arial", "B", 11)
    pdf.cell(20, 8, "ID", border=1)
    pdf.cell(80, 8, "Produto", border=1)
    pdf.cell(30, 8, "Qtd", border=1, align="R")
    pdf.cell(30, 8, "Preço (R$)", border=1, align="R")
    pdf.ln()
    pdf.set_font("Arial", size=11)
    for p in produtos:
        pdf.cell(20, 8, str(p[0]), border=1)
        name = p[1][:40]
        pdf.cell(80, 8, name, border=1)
        pdf.cell(30, 8, str(p[2]), border=1, align="R")
        pdf.cell(30, 8, f"{p[3]:.2f}", border=1, align="R")
        pdf.ln()

    pdf.ln(8)
    # Vendas
    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 8, "Vendas (mais recentes primeiro)", ln=True)
    pdf.ln(2)
    pdf.set_font("Arial", "B", 10)
    pdf.cell(12, 8, "ID", border=1)
    pdf.cell(70, 8, "Produto", border=1)
    pdf.cell(18, 8, "Qtd", border=1, align="R")
    pdf.cell(30, 8, "Unit (R$)", border=1, align="R")
    pdf.cell(30, 8, "Total (R$)", border=1, align="R")
    pdf.cell(30, 8, "Data", border=1)
    pdf.ln()
    pdf.set_font("Arial", size=10)
    for v in vendas:
        pdf.cell(12, 8, str(v[0]), border=1)
        name = v[1][:40]
        pdf.cell(70, 8, name, border=1)
        pdf.cell(18, 8, str(v[2]), border=1, align="R")
        pdf.cell(30, 8, f"{v[3]:.2f}", border=1, align="R")
        pdf.cell(30, 8, f"{v[4]:.2f}", border=1, align="R")
        pdf.cell(30, 8, v[5].split(" ")[0], border=1)
        pdf.ln()

    try:
        pdf.output(filepath)
        messagebox.showinfo("Relatório", f"Relatório salvo em:\n{filepath}")
    except Exception as e:
        messagebox.showerror("Erro", f"Não foi possível salvar PDF:\n{e}")

# ------------------ TELA ------------------
root = Tk()
root.title("Sistema de Estoque Profissional")
root.geometry("1000x650")
root.resizable(True, True)

# Frames de produto e vendas
frame_esquerdo = Frame(root, padx=10, pady=10)
frame_esquerdo.pack(side=LEFT, fill=Y)

Label(frame_esquerdo, text="Produtos", font=("Arial", 14, "bold")).pack()

frm_inputs = Frame(frame_esquerdo)
frm_inputs.pack(pady=6)

Label(frm_inputs, text="Nome:").grid(row=0, column=0, sticky=W)
entry_nome = Entry(frm_inputs, width=30)
entry_nome.grid(row=0, column=1)

Label(frm_inputs, text="Quantidade:").grid(row=1, column=0, sticky=W)
entry_qtd = Entry(frm_inputs, width=30)
entry_qtd.grid(row=1, column=1)

Label(frm_inputs, text="Preço (R$):").grid(row=2, column=0, sticky=W)
entry_preco = Entry(frm_inputs, width=30)
entry_preco.grid(row=2, column=1)

btn_frame = Frame(frame_esquerdo)
btn_frame.pack(pady=8)
Button(btn_frame, text="Adicionar", width=12, command=adicionar_produto).grid(row=0, column=0, padx=3)
Button(btn_frame, text="Editar", width=12, command=editar_produto).grid(row=0, column=1, padx=3)
Button(btn_frame, text="Excluir", width=12, command=excluir_produto).grid(row=0, column=2, padx=3)
Button(btn_frame, text="Gerar PDF", width=12, command=gerar_relatorio_pdf).grid(row=0, column=3, padx=3)

# Treeview produtos
cols = ("ID", "Nome", "Quantidade", "Preço")
tree_produtos = ttk.Treeview(root, columns=cols, show="headings", height=15)
for c in cols:
    tree_produtos.heading(c, text=c)
    if c == "Nome":
        tree_produtos.column(c, width=420)
    else:
        tree_produtos.column(c, width=100, anchor=CENTER)
tree_produtos.pack(padx=10, pady=10, fill=X)
tree_produtos.bind("<<TreeviewSelect>>", selecionar_produto)

# Frame vendas
frame_vendas = Frame(root, padx=10, pady=10)
frame_vendas.pack(fill=BOTH, expand=True)

Label(frame_vendas, text="Controle de Vendas", font=("Arial", 14, "bold")).pack(anchor=W)

frm_venda_inputs = Frame(frame_vendas)
frm_venda_inputs.pack(anchor=W, pady=6)

Label(frm_venda_inputs, text="Produto:").grid(row=0, column=0, sticky=W)
combo_venda_produto = ttk.Combobox(frm_venda_inputs, width=60)
combo_venda_produto.grid(row=0, column=1, padx=6)

Label(frm_venda_inputs, text="Quantidade:").grid(row=1, column=0, sticky=W)
entry_venda_qtd = Entry(frm_venda_inputs, width=10)
entry_venda_qtd.grid(row=1, column=1, sticky=W, padx=6)

btn_venda = Frame(frm_venda_inputs)
btn_venda.grid(row=2, column=1, pady=6, sticky=W)
Button(btn_venda, text="Registrar Venda", command=realizar_venda, width=20).grid(row=0, column=0)

# Treeview vendas
cols_v = ("ID", "Produto", "Quantidade", "Unit (R$)", "Total (R$)", "Data/Hora")
tree_vendas = ttk.Treeview(frame_vendas, columns=cols_v, show="headings", height=10)
for c in cols_v:
    tree_vendas.heading(c, text=c)
    if c == "Produto":
        tree_vendas.column(c, width=300)
    else:
        tree_vendas.column(c, width=120, anchor=CENTER)
tree_vendas.pack(padx=10, pady=10, fill=BOTH, expand=True)

# Inicialização
carregar_produtos_no_combo()
listar_produtos()
listar_vendas()

# Ao fechar, fechar conexão
def on_close():
    conn.close()
    root.destroy()

root.protocol("WM_DELETE_WINDOW", on_close)
root.mainloop()
