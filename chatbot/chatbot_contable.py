import google.generativeai as genai
import tkinter as tk
from tkinter import scrolledtext, messagebox, ttk, filedialog
import threading
import os
import PyPDF2
import queue
import time
from PIL import Image, ImageTk
import base64
from io import BytesIO

class ChatbotNIF:
    def __init__(self, root):
        self.root = root
        self.setup_colors()
        self.setup_window()
        self.setup_variables()
        self.create_widgets()
        self.setup_queue()
        self.configure_api()
        
    def setup_colors(self):
        """Configura la paleta monocromática"""
        self.colors = {
            'bg': '#f5f5f5',
            'bg_secondary': '#e0e0e0',
            'text': '#212121',
            'text_secondary': '#424242',
            'accent': '#616161',
            'accent_dark': '#424242',
            'success': '#9e9e9e',
            'error': '#616161',
            'chat_bg': '#ffffff',
            'user_bubble': '#e0e0e0',
            'bot_bubble': '#f5f5f5'
        }
        
    def setup_window(self):
        """Configura la ventana principal con estilo moderno monocromático"""
        self.root.title("🤖 Asistente NIF Contable")
        self.root.geometry("1000x700")
        self.root.configure(bg=self.colors['bg'])
        self.root.minsize(800, 600)
        
        # Estilo monocromático
        self.style = ttk.Style()
        self.style.theme_use('clam')
        
        # Configuraciones generales de estilo
        self.style.configure('.', background=self.colors['bg'], foreground=self.colors['text'])
        self.style.configure('TFrame', background=self.colors['bg'])
        self.style.configure('TButton', 
                           font=('Segoe UI', 10), 
                           padding=8,
                           background=self.colors['accent'],
                           foreground='white',
                           borderwidth=0)
        self.style.map('TButton', 
                      background=[('active', self.colors['accent_dark'])])
        self.style.configure('TLabel', 
                           background=self.colors['bg'],
                           font=('Segoe UI', 9),
                           foreground=self.colors['text'])
        self.style.configure('TEntry', 
                           fieldbackground='white',
                           font=('Segoe UI', 11),
                           foreground=self.colors['text'],
                           borderwidth=1)
        
    def setup_variables(self):
        """Inicializa variables"""
        self.api_key = ""
        self.model_name = "gemini-1.5-flash-latest"
        self.nif_knowledge = ""
        self.current_file = ""
        self.is_processing = False
        self.typing_indicator = None
        
    def setup_queue(self):
        """Configura el sistema de colas para actualizaciones seguras"""
        self.message_queue = queue.Queue()
        self.process_queue()
        
    def process_queue(self):
        """Procesa mensajes en la cola de forma segura"""
        try:
            while True:
                message_type, *args = self.message_queue.get_nowait()
                if message_type == "response":
                    self.safe_show_response(*args)
                elif message_type == "status":
                    self.update_status(*args)
                elif message_type == "typing":
                    self.update_typing_indicator(*args)
        except queue.Empty:
            pass
        finally:
            self.root.after(100, self.process_queue)
    
    def create_widgets(self):
        """Crea todos los elementos de la interfaz con estilo monocromático"""
        # Frame principal
        main_frame = ttk.Frame(self.root, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Header con título
        header_frame = ttk.Frame(main_frame, style='Header.TFrame')
        header_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Estilo para el header
        self.style.configure('Header.TFrame', background=self.colors['accent'])
        self.style.configure('Header.TLabel', 
                           background=self.colors['accent'],
                           foreground='white',
                           font=('Segoe UI', 14, 'bold'))
        
        title_label = ttk.Label(
            header_frame,
            text="Asistente Contable NIF",
            style='Header.TLabel'
        )
        title_label.pack(side=tk.LEFT, padx=10)
        
        # Área de chat con estilo monocromático
        self.chat_area = scrolledtext.ScrolledText(
            main_frame,
            wrap=tk.WORD,
            state='disabled',
            font=('Segoe UI', 12),
            height=20,
            padx=15,
            pady=15,
            bg=self.colors['chat_bg'],
            relief=tk.FLAT,
            bd=0,
            highlightthickness=0,
            foreground=self.colors['text']
        )
        self.chat_area.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # Configurar estilos de texto
        self.chat_area.tag_config('user', 
                                foreground=self.colors['text'],
                                font=('Segoe UI', 12, 'bold'))
        self.chat_area.tag_config('bot', 
                                foreground=self.colors['text'],
                                font=('Segoe UI', 12))
        self.chat_area.tag_config('system', 
                                foreground=self.colors['text_secondary'],
                                font=('Segoe UI', 11, 'italic'))
        self.chat_area.tag_config('error', 
                                foreground=self.colors['error'],
                                font=('Segoe UI', 12, 'italic'))
        self.chat_area.tag_config('typing', 
                                foreground=self.colors['text_secondary'],
                                font=('Segoe UI', 11, 'italic'))
        
        # Frame de entrada
        input_frame = ttk.Frame(main_frame)
        input_frame.pack(fill=tk.X)
        
        self.user_input = ttk.Entry(
            input_frame,
            font=('Segoe UI', 12)
        )
        self.user_input.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))
        self.user_input.bind("<Return>", self.send_message)
        
        send_btn = ttk.Button(
            input_frame,
            text="Enviar",
            command=self.send_message
        )
        send_btn.pack(side=tk.LEFT)
        
        # Botones de acción
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X, pady=(10, 0))
        
        load_btn = ttk.Button(
            btn_frame,
            text="📂 Cargar Base",
            command=self.load_knowledge
        )
        load_btn.pack(side=tk.LEFT)
        
        clear_btn = ttk.Button(
            btn_frame,
            text="🔄 Nueva Conversación",
            command=self.new_chat
        )
        clear_btn.pack(side=tk.LEFT, padx=10)
        
        # Barra de estado
        self.status_var = tk.StringVar()
        self.status_var.set("Listo")
        
        status_bar = ttk.Frame(main_frame, height=25, style='Status.TFrame')
        self.style.configure('Status.TFrame', background=self.colors['bg_secondary'])
        
        ttk.Label(
            status_bar,
            textvariable=self.status_var,
            relief=tk.SUNKEN,
            anchor=tk.W,
            font=('Segoe UI', 9),
            background=self.colors['bg_secondary'],
            foreground=self.colors['text'],
            padding=(10, 0)
        ).pack(fill=tk.X)
        
        status_bar.pack(fill=tk.X, pady=(10, 0))
        
        # Mensaje inicial
        self.add_to_chat("Sistema", "Chatbot de NIF listo. Carga un archivo PDF o TXT con información sobre NIF para comenzar.")
    
    def configure_api(self):
        """Configura la API de Gemini"""
        try:
            genai.configure(api_key=self.api_key)
            self.model = genai.GenerativeModel(
                self.model_name,
                generation_config={
                    "temperature": 0.3,
                    "max_output_tokens": 1000,
                }
            )
            self.chat = self.model.start_chat(history=[])
            self.update_status("API configurada correctamente")
            return True
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo configurar la API: {str(e)}")
            self.update_status(f"Error: {str(e)}", is_error=True)
            return False
    
    def load_knowledge(self):
        """Carga un archivo con conocimiento sobre NIF"""
        if self.is_processing:
            return
            
        file_path = filedialog.askopenfilename(
            title="Seleccionar archivo de conocimiento",
            filetypes=[
                ("Archivos PDF", "*.pdf"),
                ("Archivos de texto", "*.txt"),
                ("Todos los archivos", "*.*")
            ]
        )
        
        if file_path:
            self.is_processing = True
            threading.Thread(
                target=self.process_file_loading,
                args=(file_path,),
                daemon=True
            ).start()
    
    def process_file_loading(self, file_path):
        """Procesa la carga del archivo en segundo plano"""
        try:
            start_time = time.time()
            
            if file_path.lower().endswith('.pdf'):
                with open(file_path, 'rb') as f:
                    reader = PyPDF2.PdfReader(f)
                    text = "\n".join([page.extract_text() for page in reader.pages[:50]])  # Limitar a 50 páginas
            else:
                with open(file_path, 'r', encoding='utf-8') as f:
                    text = f.read()
            
            if text.strip():
                self.nif_knowledge = text
                self.current_file = os.path.basename(file_path)
                load_time = time.time() - start_time
                
                self.message_queue.put((
                    "status", 
                    f"Base cargada: {self.current_file} ({load_time:.1f}s)",
                    False
                ))
                self.message_queue.put((
                    "response",
                    f"Base de conocimiento actualizada: {self.current_file}",
                    None,
                    False
                ))
            else:
                self.message_queue.put((
                    "status",
                    "El archivo está vacío o no se pudo leer",
                    True
                ))
                
        except Exception as e:
            self.message_queue.put((
                "status",
                f"Error al cargar archivo: {str(e)}",
                True
            ))
        finally:
            self.is_processing = False
    
    def new_chat(self):
        """Inicia una nueva conversación"""
        if hasattr(self, 'chat'):
            self.chat = self.model.start_chat(history=[])
            self.chat_area.config(state='normal')
            self.chat_area.delete(1.0, tk.END)
            self.chat_area.config(state='disabled')
            self.add_to_chat("Sistema", "Nueva conversación iniciada")
            if self.current_file:
                self.add_to_chat("Sistema", f"Base activa: {self.current_file}")
    
    def send_message(self, event=None):
        """Envía un mensaje al chatbot"""
        if self.is_processing:
            return
            
        message = self.user_input.get().strip()
        if not message:
            return
            
        self.user_input.delete(0, tk.END)
        self.user_input.config(state='disabled')
        self.add_to_chat("Tú", message)
        
        # Respuesta inmediata para saludos
        if message.lower() in ["hola", "hi", "hello"]:
            self.add_to_chat("Bot", "👋 Hola, soy tu asistente especializado en NIF. ¿En qué puedo ayudarte hoy?")
            self.user_input.config(state='normal')
            return
            
        # Mostrar indicador de "escribiendo"
        self.show_typing_indicator()
        self.update_status("Generando respuesta...")
        self.is_processing = True
        
        # Procesar en segundo plano
        threading.Thread(
            target=self.generate_response,
            args=(message,),
            daemon=True
        ).start()
    
    def show_typing_indicator(self):
        """Muestra indicador de que el bot está escribiendo"""
        self.chat_area.config(state='normal')
        self.chat_area.insert(tk.END, "✍️ ", 'typing')
        self.typing_indicator = self.chat_area.insert(tk.END, "Bot está escribiendo...\n", 'typing')
        self.chat_area.config(state='disabled')
        self.chat_area.see(tk.END)
    
    def update_typing_indicator(self, remove=False):
        """Actualiza el indicador de typing"""
        self.chat_area.config(state='normal')
        if remove and self.typing_indicator:
            self.chat_area.delete(self.typing_indicator + "-1c", self.typing_indicator + " lineend+1c")
        self.chat_area.config(state='disabled')
    
    def generate_response(self, message):
        """Genera la respuesta del chatbot"""
        try:
            start_time = time.time()
            
            if not self.nif_knowledge:
                response = "⚠️ Por favor carga primero un archivo con conocimiento sobre NIF usando el botón 'Cargar Base'."
            else:
                # Prompt optimizado para respuestas concisas
                prompt = f"""Eres un experto en Normas de Información Financiera (NIF). 
                Responde de manera CONCISA y ESPECÍFICA a la siguiente pregunta sobre NIF.
                Usa máximo 150 palabras y sé directo. Incluye emojis relevantes cuando sea apropiado.
                
                Base de conocimiento:
                {self.nif_knowledge[:15000]}
                
                Pregunta: {message}
                
                Reglas:
                1. Solo responde sobre temas de NIF
                2. Si la pregunta no es sobre NIF, di: "❌ Solo respondo sobre NIF"
                3. Si no encuentras la respuesta, di: "⚠️ No encontré información sobre esto en la base"
                4. Usa formato claro con puntos y saltos de línea cuando sea necesario
                """
                
                response = self.chat.send_message(prompt).text
                response = response.strip()
                
                if not response:
                    response = "⚠️ No recibí una respuesta válida del modelo. Intenta reformular tu pregunta."
            
            response_time = time.time() - start_time
            self.message_queue.put((
                "status",
                f"Respuesta generada ({response_time:.1f}s)",
                False
            ))
            self.message_queue.put((
                "typing",
                True  # Remover indicador de typing
            ))
            self.message_queue.put((
                "response",
                response,
                False
            ))
            
        except Exception as e:
            self.message_queue.put((
                "status",
                f"Error: {str(e)}",
                True
            ))
            self.message_queue.put((
                "typing",
                True
            ))
            self.message_queue.put((
                "response",
                f"❌ Error al generar respuesta: {str(e)}",
                True
            ))
        finally:
            self.is_processing = False
            self.user_input.config(state='normal')
    
    def safe_show_response(self, response, is_error=False):
        """Muestra la respuesta de manera segura"""
        try:
            self.chat_area.config(state='normal')
            
            # Mostrar respuesta con emoji
            self.chat_area.insert(tk.END, "🤖 ", 'bot')
            
            tag = 'error' if is_error else 'bot'
            self.chat_area.insert(tk.END, f"{response}\n\n", tag)
            self.chat_area.config(state='disabled')
            self.chat_area.see(tk.END)
        except Exception as e:
            print(f"Error mostrando respuesta: {str(e)}")
    
    def update_status(self, message, is_error=False):
        """Actualiza la barra de estado"""
        if is_error:
            self.status_var.set(f"❌ {message}")
        else:
            self.status_var.set(f"✓ {message}")
    
    def add_to_chat(self, sender, message):
        """Añade un mensaje al área de chat"""
        self.chat_area.config(state='normal')
        
        if sender == "Tú":
            self.chat_area.insert(tk.END, "👤 Tú: ", 'user')
        elif sender == "Error":
            self.chat_area.insert(tk.END, "❌ Error: ", 'error')
        elif sender == "Sistema":
            self.chat_area.insert(tk.END, "ℹ️ Sistema: ", 'system')
        else:
            self.chat_area.insert(tk.END, "🤖 ", 'bot')
        
        tag = 'user' if sender == "Tú" else ('error' if sender == "Error" else ('system' if sender == "Sistema" else 'bot'))
        self.chat_area.insert(tk.END, f"{message}\n\n", tag)
        self.chat_area.config(state='disabled')
        self.chat_area.see(tk.END)

if __name__ == "__main__":
    # Verificar e instalar dependencias
    try:
        import google.generativeai as genai
        import PyPDF2
    except ImportError:
        import subprocess
        import sys
        subprocess.run([sys.executable, "-m", "pip", "install", "google-generativeai", "PyPDF2"])
        import google.generativeai as genai
        import PyPDF2
    
    root = tk.Tk()
    app = ChatbotNIF(root)
    root.mainloop()