import customtkinter as ctk
from tkinter import filedialog

arquivo_excel = ""

def selecionar_arquivo():
    global arquivo_excel

    arquivo_excel = filedialog.askopenfilename(
        filetypes=[("Excel", "*.xlsx")]
    )

    if arquivo_excel:
        label_arquivo.configure(text=arquivo_excel)

def executar():
    status.configure(text="Processando...")

    # Aqui vamos chamar a lógica
    # processar_excel(arquivo_excel)

    status.configure(text="Concluído!")

ctk.set_appearance_mode("dark")

app = ctk.CTk()
app.geometry("700x400")
app.title("ABC Aprendiz")

titulo = ctk.CTkLabel(
    app,
    text="Sistema de Ensalamento",
    font=("Arial", 24, "bold")
)
titulo.pack(pady=20)

btn_arquivo = ctk.CTkButton(
    app,
    text="Selecionar Excel",
    command=selecionar_arquivo
)
btn_arquivo.pack(pady=10)

label_arquivo = ctk.CTkLabel(
    app,
    text="Nenhum arquivo selecionado"
)
label_arquivo.pack()

btn_executar = ctk.CTkButton(
    app,
    text="Executar Ensalamento",
    command=executar
)
btn_executar.pack(pady=20)

status = ctk.CTkLabel(
    app,
    text="Aguardando..."
)
status.pack()

app.mainloop()