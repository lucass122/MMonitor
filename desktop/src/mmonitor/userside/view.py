import tkinter as tk
from threading import Thread
from time import sleep
from tkinter import filedialog
from tkinter import simpledialog
from tkinter import ttk
from webbrowser import open_new

from requests import post

from build import ROOT
from mmonitor.dashapp.index import Index
from mmonitor.database.mmonitor_db import MMonitorDBInterface
from mmonitor.userside.centrifuge import CentrifugeRunner
from mmonitor.userside.functional_analysis import FunctionalAnalysisRunner

"""
This file represents the basic gui for the desktop app. It is the entry point for the program and the only way 
for the user to create projects, select files and run MMonitor's computational engine (centrifuge at this moment)
"""


def require_project(func):
    """Decorator that ensures that a database was selected or created by the user."""
    def func_wrapper(*args):
        obj: GUI = args[0]
        if obj.db_path is not None and len(obj.db_path) > 0:
            return func(*args)
        else:
            obj.open_popup("Please first create or choose a project data base.", "No data base chosen")
    return func_wrapper


def require_centrifuge(func):
    """Decorator that ensures that a centrifuge index was selected by the user."""
    def func_wrapper(*args):
        obj: GUI = args[0]
        if obj.centrifuge_index is not None and len(obj.centrifuge_index) > 0:
            return func(*args)
        else:
            obj.open_popup("Please first select a centrifuge index before analyzing files.", "Centrifuge error")
    return func_wrapper


class GUI:

    def __init__(self):
        # declare data base class variable, to be chosen by user with choose_project()
        self.db: MMonitorDBInterface = None
        self.db_path = None
        self.centrifuge_index = None
        self.cent = CentrifugeRunner()
        self.func = FunctionalAnalysisRunner()
        self.dashapp = None
        self.monitor_thread = None
        self.root = tk.Tk()
        self.init_layout()
        self.taxonomy = tk.BooleanVar()
        self.assembly = tk.BooleanVar()
        self.correction = tk.BooleanVar()
        self.binning = tk.BooleanVar()
        self.annotation = tk.BooleanVar()
        self.kegg = tk.BooleanVar()

    def init_layout(self):

        self.root.geometry("350x250")
        self.root.title("MMonitor v0.1.0. alpha")
        self.root.resizable(width=False, height=True)
        self.width = 20
        self.height = 1
        # create buttons
        tk.Button(self.root, text="Create Project", command=self.create_project,
                  padx=10, pady=5, width=self.width, height=self.height, fg='white', bg='#254D25').pack()
        tk.Button(self.root, text="Choose Project", command=self.choose_project,
                  padx=10, pady=5, width=self.width, height=self.height, fg='white', bg='#254D25').pack()
        # tk.Button(self.root, text="Choose centrifuge index", command=self.choose_index,
        #           padx=10, pady=5, width=self.width,height=self.height, fg='white', bg='#254D25').pack()
        # # tk.Button(self.root, text="Analyze fastq in folder", command=self.analyze_fastq_in_folder,
        #           padx=10, pady=5, width=self.width,height=self.height, fg='white', bg='#254D25').pack()
        tk.Button(self.root, text="Add metadata from CSV", command=self.append_metadata,
                  padx=10, pady=5, width=self.width, height=self.height, fg='white', bg='#254D25').pack()
        tk.Button(self.root, text="Run analysis pipeline", command=self.checkbox_popup,
                  padx=10, pady=5, width=self.width, height=self.height, fg='white', bg='#254D25').pack()

        tk.Button(self.root, text="Start monitoring", command=self.start_monitoring,
                  padx=10, pady=5, width=self.width, height=self.height, fg='white', bg='#254D25').pack()
        tk.Button(self.root, text="Quit",
                  padx=10, pady=5, width=self.width, height=self.height, fg='white', bg='#254D25',
                  command=self.stop_app).pack()

    def open_popup(self, text, title):
        top = tk.Toplevel(self.root)
        top.geometry("700x300")
        top.title(title)
        tk.Label(top, text=text, font='Mistral 18 bold').place(x=150, y=80)
        tk.Button(top, text="Okay", command=top.destroy).pack()

    def create_project(self):
        filename = filedialog.asksaveasfilename(
            initialdir='projects/',
            title="Choose place to safe the project data"
        )
        filename += ".sqlite3"
        self.db_path = filename
        self.db = MMonitorDBInterface(filename)
        self.db.create_db(filename)

    def choose_project(self):

        self.db_path = filedialog.askopenfilename(
            initialdir='projects/',
            title="Choose project data base to use",
            filetypes=(("sqlite", "*.sqlite3"), ("all files", "*.*"))
        )
        self.db = MMonitorDBInterface(self.db_path)
        # self.db = "mmonitor.sqlite3"

    def choose_index(self):
        self.centrifuge_index = filedialog.askopenfilename(
            initialdir='projects/',
            title="Choose project data base to use",
            filetypes=(("sqlite", "*.sqlite3"), ("all files", "*.*"))
        )

    @require_project
    def append_metadata(self):
        csv_file = filedialog.askopenfilename(
            initialdir='projects/',
            title="Choose csv file containing metadata to append",
            filetypes=(("csv", "*.csv"), ("all files", "*.*"))
        )
        if csv_file is not None and len(csv_file) > 0:
            self.db.append_metadata_from_csv(csv_file)

    # choose folder containing sequencing data
    # TODO: check if there is white space in path that causes problem
    @require_project
    @require_centrifuge
    def analyze_fastq_in_folder(self):
        folder = filedialog.askdirectory(
            initialdir='/',
            title="Choose directory containing sequencing data"
        )
        files = self.cent.get_files_from_folder(folder)

        sample_name = simpledialog.askstring(
            "Input sample name",
            "What should the sample be called?",
            parent=self.root
        )
        self.cent.run_centrifuge(files, self.centrifuge_index, sample_name)

        self.cent.make_kraken_report(self.centrifuge_index)
        self.db.update_table_with_kraken_out(f"classifier_out/{sample_name}_kraken_out", "S", sample_name, "project")

    def checkbox_popup(self):
        # open checkbox to ask what the user wants to run (in case of rerunning)
        top = tk.Toplevel(self.root)
        top.geometry("400x300")
        top.title("Select analysis steps to perform.")
        c6 = ttk.Checkbutton(top, text='Taxonomic analysis', variable=self.taxonomy)
        c1 = ttk.Checkbutton(top, text='Assembly', variable=self.assembly)
        c2 = ttk.Checkbutton(top, text='Correction', variable=self.correction)
        c3 = ttk.Checkbutton(top, text='Binning', variable=self.binning)
        c4 = ttk.Checkbutton(top, text='Annotation', variable=self.annotation)
        c5 = ttk.Checkbutton(top, text='KEGG', variable=self.kegg)
        c6.pack()
        c1.pack()
        c2.pack()
        c3.pack()
        c4.pack()
        c5.pack()

        tk.Label(top, text="Please select which parts of the pipeline you want to run.", font='Mistral 12 bold').place(
            x=0, y=200)
        tk.Button(top, text="Continue", command=lambda: [self.run_analysis_pipeline(), top.destroy()]).pack()

    def ask_sample_name(self):
        sample_name = simpledialog.askstring(
            "Input sample name",
            "What should the sample be called?",
            parent=self.root
        )
        return sample_name

    # @require_project
    def run_analysis_pipeline(self):
        if self.assembly.get() or self.correction.get():
            seq_file = filedialog.askopenfilename(title="Please select a sequencing file")
        if self.assembly.get() or self.correction.get() or self.annotation.get() or self.binning.get():
            sample_name = self.ask_sample_name()
            self.func.check_software_avail()
        if self.taxonomy.get():
            self.analyze_fastq_in_folder()
        if self.assembly.get():
            self.func.run_flye(seq_file, sample_name)
        if self.correction.get():
            self.func.run_racon(seq_file, sample_name)
            # self.func.run_medaka(seq_file, sample_name) TODO: FIX MEDAKA
        if self.binning.get():
            self.func.run_binning(sample_name)
        if self.annotation.get():
            bins_path = f"{ROOT}/src/resources/{sample_name}/bins/"
            self.func.run_prokka(bins_path)
        if self.kegg.get():
            sample_name = self.ask_sample_name()

            pipeline_out = f"{ROOT}/src/resources/pipeline_out/{sample_name}/"
            self.kegg_thread1 = Thread(target=self.func.create_keggcharter_input(pipeline_out))
            self.kegg_thread1.start()
            self.kegg_thread2 = Thread(self.func.run_keggcharter(pipeline_out, f"{pipeline_out}/keggcharter.tsv"))
            self.kegg_thread2.start()

    @require_project
    def start_monitoring(self):
        self.dashapp = Index(self.db)
        self.monitor_thread = Thread(target=self.dashapp.run_server, args=(False,))
        self.monitor_thread.start()

        sleep(1)
        open_new('http://localhost:8050')

    def start_app(self):
        self.root.mainloop()

    def stop_app(self):
        if self.monitor_thread is not None and self.monitor_thread.is_alive():
            post('http://localhost:8050/shutdown')
            self.monitor_thread.join()
        self.root.destroy()
