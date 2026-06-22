import tkinter as tk
from tkinter import ttk
import cv2
from PIL import Image, ImageTk
import threading

class MultiCameraVAR:
    def __init__(self, window):
        self.window = window
        self.window.title("PRO VAR SYSTEM - MULTI-CAM EDITION (4x USB)")
        self.window.geometry("1100x750")
        self.window.configure(bg="#1a1a1a")

        # Configurações de Câmeras (IDs das portas USB do Windows/Linux)
        # 0 é geralmente a webcam interna, 1, 2, 3 são as USBs adicionais
        self.camera_ids = [0, 1, 2, 3] 
        self.caps = [None] * 4
        self.selected_cam = 0 # Câmera em foco analítico
        
        # Variáveis de Controle
        self.playback_speed = 30 
        self.zoom_level = 1.0
        self.is_running = True
        
        self.create_widgets()
        self.init_cameras()
        
        # Thread para ler as câmeras sem travar a interface de usuário (UI)
        self.update_thread = threading.Thread(target=self.stream_cameras, daemon=True)
        self.update_thread.start()
        
        self.window.protocol("WM_DELETE_WINDOW", self.on_close)

    def create_widgets(self):
        # Painel Superior
        top_panel = tk.Frame(self.window, bg="#2d2d2d", height=50)
        top_panel.pack(fill=tk.X, side=tk.TOP)

        tk.Label(top_panel, text="SISTEMA DE VAR MULTI-CÂMERAS LIVE", fg="#00ffcc", bg="#2d2d2d", font=("Arial", 12, "bold")).pack(side=tk.LEFT, padx=15, pady=10)
        
        # Seletor de foco manual
        tk.Label(top_panel, text="FOCO ANALÍTICO:", fg="white", bg="#2d2d2d").pack(side=tk.LEFT, padx=5)
        self.cam_focus_var = tk.StringVar(value="Câmera 1")
        cam_combo = ttk.Combobox(top_panel, textvariable=self.cam_focus_var, values=["Câmera 1", "Câmera 2", "Câmera 3", "Câmera 4"], state="readonly", width=10)
        cam_combo.pack(side=tk.LEFT, padx=5)
        cam_combo.bind("<<ComboboxSelected>>", self.change_focus)

        # Grade de Câmeras (2x2)
        self.grid_frame = tk.Frame(self.window, bg="black")
        self.grid_frame.pack(pady=10, fill=tk.BOTH, expand=True)
        
        self.canvas_list = []
        for i in range(4):
            row = i // 2
            col = i % 2
            # Borda amarela indica qual câmera está selecionada para efeitos de Zoom
            highlight_thickness = 2 if i == self.selected_cam else 0
            canvas = tk.Canvas(self.grid_frame, bg="#111", width=500, height=280, highlightbackground="#00ffcc", highlightthickness=highlight_thickness)
            canvas.grid(row=row, column=col, padx=5, pady=5, sticky="nsew")
            self.canvas_list.append(canvas)
            
            # Permite selecionar a câmera clicando direto nela
            canvas.bind("<Button-1>", lambda event, cam_id=i: self.select_cam_by_click(cam_id))

        self.grid_frame.grid_rowconfigure(0, weight=1)
        self.grid_frame.grid_rowconfigure(1, weight=1)
        self.grid_frame.grid_columnconfigure(0, weight=1)
        self.grid_frame.grid_columnconfigure(1, weight=1)

        # Painel de Controle Inferior
        control_panel = tk.Frame(self.window, bg="#2d2d2d")
        control_panel.pack(fill=tk.X, side=tk.BOTTOM, pady=5)

        btn_container = tk.Frame(control_panel, bg="#2d2d2d")
        btn_container.pack(pady=10)

        # Controles de Câmera Lenta por Software
        tk.Label(btn_container, text="VELOCIDADE DO FEED:", fg="white", bg="#2d2d2d", font=("Arial", 9, "bold")).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_container, text="LIVE (100%)", command=lambda: self.change_speed(30), bg="#28a745", fg="white").pack(side=tk.LEFT, padx=2)
        tk.Button(btn_container, text="SLOW (50%)", command=lambda: self.change_speed(60), bg="#ffc107", fg="black").pack(side=tk.LEFT, padx=2)
        tk.Button(btn_container, text="SUPER SLOW (25%)", command=lambda: self.change_speed(120), bg="#dc3545", fg="white").pack(side=tk.LEFT, padx=2)

        # Controles de Zoom Analítico (Aplica na câmera focada)
        tk.Label(btn_container, text="   ZOOM LUPA (CAM FOCADA):", fg="white", bg="#2d2d2d", font=("Arial", 9, "bold")).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_container, text="1x Normal", command=lambda: self.set_zoom(1.0), bg="#555", fg="white").pack(side=tk.LEFT, padx=2)
        tk.Button(btn_container, text="2x Zoom", command=lambda: self.set_zoom(2.0), bg="#555", fg="white").pack(side=tk.LEFT, padx=2)
        tk.Button(btn_container, text="4x Zoom", command=lambda: self.set_zoom(4.0), bg="#555", fg="white").pack(side=tk.LEFT, padx=2)

        # Barra de Status
        self.lbl_status = tk.Label(self.window, text="SISTEMA MULTI-CAM OPERACIONAL", bg="#1a1a1a", fg="#00ffcc", font=("Courier", 11, "bold"))
        self.lbl_status.pack(side=tk.BOTTOM, fill=tk.X)

    def init_cameras(self):
        """Inicializa as conexões com os dispositivos USB conectados"""
        for i, cam_id in enumerate(self.camera_ids):
            cap = cv2.VideoCapture(cam_id)
            if cap.isOpened():
                # Define resolução menor para otimizar o processamento de 4 câmeras simultâneas
                cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
                self.caps[i] = cap
            else:
                print(f"Aviso: Câmera USB no índice {cam_id} não encontrada.")

    def stream_cameras(self):
        """Loop de captura executado em segundo plano (Thread)"""
        while self.is_running:
            for i in range(4):
                cap = self.caps[i]
                if cap and cap.isOpened():
                    ret, frame = cap.read()
                    if ret:
                        # Se for a câmera selecionada, aplica o Zoom digital se configurado
                        if i == self.selected_cam and self.zoom_level > 1.0:
                            h, w, _ = frame.shape
                            cx, cy = w // 2, h // 2
                            bx, by = int(w / (2 * self.zoom_level)), int(h / (2 * self.zoom_level))
                            frame = frame[cy-by:cy+by, cx-bx:cx+bx]

                        # Redimensiona para encaixar no quadrante correspondente
                        frame = cv2.resize(frame, (500, 260))

                        # Desenha Telemetria e identificação na imagem
                        color = (0, 255, 255) if i == self.selected_cam else (255, 255, 255)
                        cv2.putText(frame, f"CAM {i+1} {'[FOCO]' if i == self.selected_cam else ''}", 
                                    (15, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
                        
                        if self.playback_speed > 30 and i == self.selected_cam:
                            cv2.putText(frame, "SLOW-MO ACTIVE", (330, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)

                        # Converte formato OpenCV (BGR) para Tkinter (RGB)
                        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                        img = Image.fromarray(frame)
                        img_tk = ImageTk.PhotoImage(image=img)

                        # Atualiza o canvas específico da câmera com segurança (Thread-safe)
                        self.window.after(0, self.update_canvas, i, img_tk)
            
            # Controla a taxa de atualização global (Simula Câmera Lenta)
            cv2.waitKey(self.playback_speed)

    def update_canvas(self, index, img_tk):
        if self.is_running:
            self.canvas_list[index].create_image(0, 0, anchor=tk.NW, image=img_tk)
            self.canvas_list[index].image = img_tk

    def change_focus(self, event):
        """Muda o foco através do menu Combobox superior"""
        cam_idx = int(self.cam_focus_var.get().split(" ")[1]) - 1
        self.select_camera(cam_idx)

    def select_cam_by_click(self, cam_id):
        """Muda o foco clicando diretamente em cima do quadrante da câmera"""
        self.cam_focus_var.set(f"Câmera {cam_id + 1}")
        self.select_camera(cam_id)

    def select_camera(self, cam_id):
        self.selected_cam = cam_id
        # Reseta o zoom ao trocar de câmera para evitar distorções abruptas
        self.zoom_level = 1.0 
        
        # Atualiza as bordas de destaque visual na interface
        for i, canvas in enumerate(self.canvas_list):
            if i == self.selected_cam:
                canvas.config(highlightthickness=3, highlightbackground="#ffcc00")
            else:
                canvas.config(highlightthickness=0)
                
        self.lbl_status.config(text=f"Analisando Câmera {cam_id + 1} | Zoom atual: {self.zoom_level}x")

    def change_speed(self, speed):
        self.playback_speed = speed

    def set_zoom(self, level):
        self.zoom_level = level
        self.lbl_status.config(text=f"Analisando Câmera {self.selected_cam + 1} | Zoom atual: {self.zoom_level}x")

    def on_close(self):
        """Fecha as conexões de hardware e desliga threads de forma limpa"""
        self.is_running = False
        for cap in self.caps:
            if cap and cap.isOpened():
                cap.release()
        self.window.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = MultiCameraVAR(root)
    root.mainloop()
