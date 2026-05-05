#!/usr/bin/env python3
"""
Interface grafica pra gerar posts em batch a partir de .txt.

Como usar:
    python generate-gui.py

A janela abre, voce seleciona os .txt, ajusta opcoes, clica GERAR.
Cada .txt vira um post HTML completo, opcionalmente publicado direto no GitHub.
"""

import os
import sys
import subprocess
import threading
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, ttk, scrolledtext, messagebox

PROJECT_ROOT = Path(__file__).parent
GENERATOR = PROJECT_ROOT / 'generate-post.py'


class GeneratorGUI:
    def __init__(self, root):
        self.root = root
        root.title('Noticia Reality - Gerador de Posts')
        root.geometry('840x680')
        root.configure(bg='#fafafa')

        self.files = []
        self._build_ui()

    def _build_ui(self):
        # Header vermelho
        header = tk.Frame(self.root, bg='#dc2626', height=64)
        header.pack(fill='x')
        header.pack_propagate(False)
        tk.Label(header, text='NOTICIA REALITY', bg='#dc2626', fg='white',
                 font=('Georgia', 18, 'bold')).pack(side='left', padx=20, pady=14)
        tk.Label(header, text='Gerador de Posts', bg='#dc2626', fg='#fbbf24',
                 font=('Arial', 10, 'italic')).pack(side='left', pady=20)

        # Subheader: botoes selecao
        sub = tk.Frame(self.root, bg='#fafafa', pady=12)
        sub.pack(fill='x', padx=14)

        tk.Button(sub, text='Selecionar TXTs', command=self.select_files,
                  bg='#dc2626', fg='white', font=('Arial', 10, 'bold'),
                  padx=18, pady=8, relief='flat', cursor='hand2').pack(side='left')

        tk.Button(sub, text='Adicionar pasta inteira', command=self.select_folder,
                  bg='#171717', fg='white', font=('Arial', 10),
                  padx=14, pady=8, relief='flat', cursor='hand2').pack(side='left', padx=8)

        tk.Button(sub, text='Limpar', command=self.clear_files,
                  bg='#737373', fg='white', font=('Arial', 10),
                  padx=14, pady=8, relief='flat', cursor='hand2').pack(side='left')

        self.count_lbl = tk.Label(sub, text='0 arquivos', bg='#fafafa',
                                   font=('Arial', 10), fg='#737373')
        self.count_lbl.pack(side='right')

        # Lista de arquivos
        list_frame = tk.LabelFrame(self.root, text=' Arquivos selecionados ',
                                    bg='#fafafa', font=('Arial', 10, 'bold'),
                                    padx=8, pady=8)
        list_frame.pack(fill='both', expand=True, padx=14, pady=4)

        self.listbox = tk.Listbox(list_frame, font=('Consolas', 9), bg='white',
                                   selectmode='extended', activestyle='none',
                                   borderwidth=1, relief='solid', highlightthickness=0)
        scroll = tk.Scrollbar(list_frame, command=self.listbox.yview)
        self.listbox.config(yscrollcommand=scroll.set)
        scroll.pack(side='right', fill='y')
        self.listbox.pack(side='left', fill='both', expand=True)

        # Configuracoes
        cfg = tk.LabelFrame(self.root, text=' Opcoes ',
                             bg='#fafafa', font=('Arial', 10, 'bold'),
                             padx=14, pady=10)
        cfg.pack(fill='x', padx=14, pady=4)

        tk.Label(cfg, text='Categoria:', bg='#fafafa').grid(row=0, column=0, sticky='w')
        self.category = ttk.Combobox(cfg, values=['auto', 'lcdlf', 'gh', 'farandula'],
                                       state='readonly', width=14)
        self.category.set('auto')
        self.category.grid(row=0, column=1, padx=8, pady=4)

        tk.Label(cfg, text='Cor do hero:', bg='#fafafa').grid(row=0, column=2, sticky='w', padx=(20, 0))
        self.color = ttk.Combobox(cfg, values=['auto', 'red', 'blue', 'purple', 'orange', 'gold', 'green'],
                                    state='readonly', width=14)
        self.color.set('auto')
        self.color.grid(row=0, column=3, padx=8, pady=4)

        self.update_home_var = tk.BooleanVar(value=True)
        tk.Checkbutton(cfg, text='Adicionar na homepage (Ultima hora)',
                       variable=self.update_home_var, bg='#fafafa').grid(row=1, column=0, columnspan=2, sticky='w', pady=(10, 0))

        self.auto_push_var = tk.BooleanVar(value=True)
        tk.Checkbutton(cfg, text='Commit + push para o GitHub depois',
                       variable=self.auto_push_var, bg='#fafafa').grid(row=1, column=2, columnspan=2, sticky='w', pady=(10, 0))

        # Botao principal
        self.go_btn = tk.Button(self.root, text='GERAR E PUBLICAR',
                                 command=self.start_generation,
                                 bg='#dc2626', fg='white',
                                 font=('Arial', 13, 'bold'),
                                 pady=14, relief='flat', cursor='hand2')
        self.go_btn.pack(fill='x', padx=14, pady=8)

        # Progress bar
        self.progress = ttk.Progressbar(self.root, mode='determinate')
        self.progress.pack(fill='x', padx=14)

        # Log
        log_frame = tk.LabelFrame(self.root, text=' Log ',
                                    bg='#fafafa', font=('Arial', 10, 'bold'),
                                    padx=4, pady=4)
        log_frame.pack(fill='both', expand=True, padx=14, pady=8)

        self.log = scrolledtext.ScrolledText(log_frame, height=10,
                                               font=('Consolas', 9),
                                               bg='#0a0a0a', fg='#10b981',
                                               insertbackground='#10b981',
                                               relief='flat')
        self.log.pack(fill='both', expand=True)
        self._log('Pronto. Selecione arquivos .txt e clique GERAR E PUBLICAR.\n')

    def _log(self, msg):
        self.log.insert('end', msg)
        self.log.see('end')
        self.root.update_idletasks()

    def _update_count(self):
        self.count_lbl.config(text='{} arquivo{}'.format(len(self.files), 's' if len(self.files) != 1 else ''))

    def select_files(self):
        files = filedialog.askopenfilenames(
            title='Selecione os arquivos .txt',
            filetypes=[('Arquivos de texto', '*.txt'), ('Todos', '*.*')],
            initialdir=str(PROJECT_ROOT / 'posts'),
        )
        for f in files:
            if f not in self.files:
                self.files.append(f)
                self.listbox.insert('end', Path(f).name)
        self._update_count()

    def select_folder(self):
        folder = filedialog.askdirectory(
            title='Selecione uma pasta com .txt',
            initialdir=str(PROJECT_ROOT / 'posts'),
        )
        if not folder:
            return
        added = 0
        for f in sorted(Path(folder).glob('*.txt')):
            sf = str(f)
            if sf not in self.files:
                self.files.append(sf)
                self.listbox.insert('end', f.name)
                added += 1
        self._log('+ {} arquivos adicionados de "{}"\n'.format(added, folder))
        self._update_count()

    def clear_files(self):
        self.files = []
        self.listbox.delete(0, 'end')
        self._update_count()

    def start_generation(self):
        if not self.files:
            messagebox.showwarning('Nenhum arquivo', 'Selecione pelo menos um arquivo .txt antes.')
            return
        self.go_btn.config(state='disabled', text='GERANDO...')
        self.progress.config(maximum=len(self.files), value=0)
        threading.Thread(target=self._run_batch, daemon=True).start()

    def _run_batch(self):
        ok, fail = 0, 0
        total = len(self.files)
        self._log('\n' + '=' * 60 + '\n')
        self._log('Processando {} arquivo(s)...\n'.format(total))
        self._log('=' * 60 + '\n')

        for i, txt_path in enumerate(self.files, 1):
            name = Path(txt_path).name
            self._log('\n[{}/{}] {}\n'.format(i, total, name))

            cmd = [sys.executable, str(GENERATOR), txt_path]
            if self.category.get() != 'auto':
                cmd += ['--category', self.category.get()]
            if self.color.get() != 'auto':
                cmd += ['--color', self.color.get()]
            if self.update_home_var.get():
                cmd += ['--update-home']

            try:
                result = subprocess.run(cmd, cwd=str(PROJECT_ROOT),
                                          capture_output=True, text=True,
                                          encoding='utf-8', errors='replace')
                if result.returncode == 0:
                    # extrai linha "Arquivo: ..." e "URL: ..."
                    for line in result.stdout.splitlines():
                        if line.startswith('URL:') or line.startswith('Titulo:'):
                            self._log('  ' + line + '\n')
                    self._log('  OK\n')
                    ok += 1
                else:
                    self._log('  ERRO: ' + (result.stderr or result.stdout)[:300] + '\n')
                    fail += 1
            except Exception as e:
                self._log('  EXCECAO: ' + str(e) + '\n')
                fail += 1

            self.progress.config(value=i)
            self.root.update_idletasks()

        self._log('\n' + '=' * 60 + '\n')
        self._log('Resultado: {} sucesso, {} falhas\n'.format(ok, fail))
        self._log('=' * 60 + '\n')

        if self.auto_push_var.get() and ok > 0:
            self._log('\nPublicando no GitHub...\n')
            try:
                subprocess.run(['git', 'add', '-A'], cwd=str(PROJECT_ROOT),
                                capture_output=True, check=True)
                msg = 'novos posts gerados ({} arquivo{})'.format(ok, 's' if ok != 1 else '')
                subprocess.run(['git', 'commit', '-m', msg], cwd=str(PROJECT_ROOT),
                                capture_output=True, check=True)
                push = subprocess.run(['git', 'push'], cwd=str(PROJECT_ROOT),
                                        capture_output=True, text=True, encoding='utf-8',
                                        errors='replace')
                if push.returncode == 0:
                    self._log('PUBLICADO! Em ~1 min vai estar online em https://noticiareality.blog\n')
                else:
                    self._log('Erro no push: ' + push.stderr + '\n')
            except subprocess.CalledProcessError as e:
                err = (e.stderr.decode('utf-8', errors='replace') if e.stderr else str(e))
                self._log('Erro no git: ' + err[:300] + '\n')

        self.go_btn.config(state='normal', text='GERAR E PUBLICAR')


if __name__ == '__main__':
    root = tk.Tk()
    app = GeneratorGUI(root)
    root.mainloop()
