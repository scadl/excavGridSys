import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, ttk
from PIL import Image, ImageTk
import json

class GridAnnotator:

    def __init__(self, master):
        self.master = master
        self.master.title("Оцифровка чертежа — Canvas")
        
        self.handle1 = None
        self.handle2 = None
        self.handle_size = 10

        self.dragging_handle = None

        self.cell_w = None
        self.cell_h = None
        self.grid_left = None
        self.grid_top = None

        # Разрешаем менять размер окна
        self.master.resizable(True, True)

        # Оригинальное изображение
        self.image = None
        self.photo = None
        self.scale = 1.0

        # Параметры сетки
        self.grid_left = None
        self.grid_top = None
        self.cell_width = None
        self.cell_height = None
        
        # timer refrecnce for detecting window resize
        self.resize_job = None

        self.letters = ["A"]
        self.numbers = ["1"]
        self.grid_data = {}
        
        self.deleted = []

        self.click_stage = 0
        
        # Создаём панель управления
        toolbar = ttk.Frame(self.master)        
        ttk.Button(toolbar, text="Загрузить чертеж", command=self.load_image).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="Задать размер сетки", command=self.start_calibration).pack(side=tk.LEFT, padx=2)
        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=5)
        ttk.Label(toolbar, text="Выберите слой:").pack(side=tk.LEFT, padx=2)
        self.grid_size_combo = ttk.Combobox(toolbar, values=[
            "Балласт",
            "СКС + БПК",
            "СПП + СС",
            "СТСС + БКУ и КЖ",
            "УМП"
        ])
        self.grid_size_combo.pack(side=tk.LEFT, padx=2)
        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=5)
        ttk.Label(toolbar, text="Сектор:").pack(side=tk.LEFT, padx=2)
        ttk.Spinbox(toolbar, from_=1, to=7, width=5).pack(side=tk.LEFT, padx=2)
        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=5)
        ttk.Label(toolbar, text="Пласт:").pack(side=tk.LEFT, padx=2)
        ttk.Spinbox(toolbar, from_=1, to=12, width=5).pack(side=tk.LEFT, padx=2)
        ttk.Separator(self.master, orient=tk.HORIZONTAL).pack(side=tk.TOP, fill=tk.X)
        ttk.Button(toolbar, text="В JSON", command=self.save_json).pack(side=tk.RIGHT, padx=2)
        ttk.Button(toolbar, text="В БД", command=self.save_db).pack(side=tk.RIGHT, padx=2)
        toolbar.pack(side=tk.TOP, fill=tk.X)
              
        # Canvas для чертежа
        self.canvas = tk.Canvas(master, bg="gray")
        self.canvas.pack(fill=tk.BOTH, expand=True)
        
        # create image container
        self.img_id = self.canvas.create_image(0, 0, anchor="nw", image=self.photo)
        # drop container to lowest layer on canvas
        self.canvas.tag_lower(self.img_id)

        # Обработчики
        self.master.bind("<Configure>", self.on_resize)
        
        
        self.create_handles()

    def create_handles(self):
        
        # REmove old handlers
        self.canvas.delete("handle1")
        self.canvas.delete("handle2")
        
        size = 50
        
        # Wait fow wind to draw. Required to get real size
        self.master.update_idletasks()
        
        print("Canvas dimensions:", self.canvas.winfo_width(), self.canvas.winfo_height())
        print("Window dimensions:", self.master.winfo_width(), self.master.winfo_height())
        
        # Примерное стартовое положение (центр экрана)
        if self.canvas.winfo_width() > size:
            cx = self.canvas.winfo_width() // 2
            cy = self.canvas.winfo_height() // 2
        else:
            cx = self.master.winfo_width() // 2
            cy = self.master.winfo_height() // 2

        # Верхний левый угол
        self.handle1 = self.canvas.create_rectangle(
            cx - size, cy - size,
            cx - size + self.handle_size, cy - size + self.handle_size,
            fill="yellow", outline="black", tags="handle1"
        )

        # Нижний правый угол
        self.handle2 = self.canvas.create_rectangle(
            cx + size, cy + size,
            cx + size + self.handle_size, cy + size + self.handle_size,
            fill="yellow", outline="black", tags="handle2"
        )
        
        self.canvas.tag_bind("handle1", "<ButtonPress-1>", self.on_handle_press)
        self.canvas.tag_bind("handle1", "<B1-Motion>", self.on_handle_drag)
        self.canvas.tag_bind("handle1", "<ButtonRelease-1>", self.on_handle_release)
        self.canvas.tag_bind("handle2", "<ButtonPress-1>", self.on_handle_press)
        self.canvas.tag_bind("handle2", "<B1-Motion>", self.on_handle_drag)
        self.canvas.tag_bind("handle2", "<ButtonRelease-1>", self.on_handle_release)
        
        self.update_grid_preview()

    def on_handle_press(self, event):
        # Определяем какой хендлер схвачен
        item = self.canvas.find_closest(event.x, event.y)[0]
        if item in (self.handle1, self.handle2):
            self.dragging_handle = item

    def on_handle_drag(self, event):
        
        # check if mouse dragging handel
        if not self.dragging_handle:
            return

        # Перемещаем хендлер
        x = event.x
        y = event.y
        self.canvas.coords(
            self.dragging_handle,
            x, y,
            x + self.handle_size, y + self.handle_size
        )

        # Перестраиваем сетку в реальном времени
        self.update_grid_preview()

    def on_handle_release(self, event):
        self.dragging_handle = None
        
    def update_grid_preview(self):
        # Получаем координаты хендлеров
        x1, y1, _, _ = self.canvas.coords(self.handle1)
        x2, y2, _, _ = self.canvas.coords(self.handle2)

        # Вычисляем размеры клетки
        self.cell_w = abs(x2 - x1)
        self.cell_h = abs(y2 - y1)

        # Верхний левый угол сетки
        self.grid_left = min(x1, x2)
        self.grid_top = min(y1, y2)

        # Удаляем старую сетку
        self.canvas.delete("grid")
        self.canvas.delete("letter")

        # Строим новую сетку
        for i, letter in enumerate(self.letters):
            for j, number in enumerate(self.numbers):
                cx1 = self.grid_left + i * self.cell_w
                cy1 = self.grid_top + j * self.cell_h
                cx2 = cx1 + self.cell_w
                cy2 = cy1 + self.cell_h

                qIndex = f"{letter}{number}"
                
                if qIndex not in self.deleted:
                    # allowed stipple: 12,25,50,75
                    self.canvas.create_rectangle(
                        cx1, cy1, cx2, cy2,
                        outline="red", width=1, 
                        fill="red", stipple="gray12",
                        tags=("grid", qIndex)
                    )
                    self.canvas.create_text(cx1 + 5, cy1 + 5, anchor="nw", 
                        text=f"{letter}{number}", fill="blue", 
                        tags=("grid", qIndex)
                    )
                
        self.rise_handeler_to_top()
                
        # Bind onMouseClick event (all mouse buttons)
        self.canvas.tag_bind("grid", "<Button>", self.on_click)
    
    # Layer management, rise grid and handlers on top  
    def rise_handeler_to_top(self):    
        self.canvas.tag_raise("grid")
        self.canvas.tag_raise("handle1")
        self.canvas.tag_raise("handle2")

    # ------------------------------------------------------------
    # Загрузка изображения
    # ------------------------------------------------------------
    def load_image(self):
        file_path = filedialog.askopenfilename()
        if not file_path:
            return

        self.image = Image.open(file_path)
        self.update_scaled_image()

    # ------------------------------------------------------------
    # Масштабирование изображения под окно
    # ------------------------------------------------------------
    def update_scaled_image(self, fast=True):
        if self.image is None:
            return

        win_w = self.master.winfo_width()
        win_h = self.master.winfo_height()

        img_w, img_h = self.image.size

        self.scale = min(win_w / img_w, win_h / img_h)

        new_w = int(img_w * self.scale)
        new_h = int(img_h * self.scale)

        # apply resize to image itself, using one of the algos
        if fast:
            resized = self.image.resize((new_w, new_h), Image.NEAREST)
        else:
            resized = self.image.resize((new_w, new_h), Image.LANCZOS)
        
        # recrate image component in new size
        self.photo = ImageTk.PhotoImage(resized)
        # insert component into form container (prepared during init)
        self.canvas.itemconfig(self.img_id, image=self.photo)
        # update canvas size with image props
        self.canvas.config(width=new_w, height=new_h)
        
        #disable timer after resize image
        if self.resize_job:
            self.master.after_cancel(self.resize_job)
            
        self.rise_handeler_to_top()

        #if self.cell_width:
        #    self.draw_grid()

    # ------------------------------------------------------------
    # Обработка изменения размера окна
    # ------------------------------------------------------------
    def on_resize(self, event):
        
        self.update_scaled_image()
        
        # if timer running, when new call happen
        if self.resize_job:
            # after_cancel() - cancel timer call, by reference
            self.master.after_cancel(self.resize_job)
        
        # after(time_ms, callback_f()) - start new timer, triggered after time passed
        self.resize_job = self.master.after(100, lambda: self.update_scaled_image(fast=False))

    # ------------------------------------------------------------
    # Калибровка сетки
    # ------------------------------------------------------------
    def start_calibration(self):
        
        letters_range = simpledialog.askstring("Диапазон букв", "Введите диапазон букв (например A-H):")
        numbers_range = simpledialog.askstring("Диапазон цифр", "Введите диапазон цифр (например 1-20):")

        start_letter, end_letter = letters_range.split("-")
        letters_raw = [chr(i) for i in range(ord(start_letter), ord(end_letter) + 1)]

        # Исключаем буквы Ё и Й
        self.letters = [L for L in letters_raw if L not in ("Ё", "Й")]

        start_num, end_num = numbers_range.split("-")
        self.numbers = list(range(int(start_num), int(end_num) + 1))
        
        self.update_grid_preview()

    # ------------------------------------------------------------
    # Обработка кликов
    # ------------------------------------------------------------
    def on_click(self, event):
        
        orig_x = int(event.x / self.scale)
        orig_y = int(event.y / self.scale)
        
        current = self.canvas.find_withtag("current")
        if current:
            tags = self.canvas.gettags(current[0])
            square_name = tags[1]
            # Event num: 1 - left click, 2 - middle click, 3 - right click
            if event.num == 1:
                print(f"Вы выбрали квадрат: {square_name}")
            if event.num == 3:
                self.canvas.delete(square_name)
                self.deleted.append(square_name)
            
            

        """"                            
        dlg = simpledialog.askstring("Слой", "Введите слой: ")
        layer = dlg

        allowed = messagebox.askyesno(
            "Использование квадрата",
            f"Можно использовать квадрат {square_name}?"
        )

        self.grid_data[square_name] = {
            "layer": layer,
            "allowed": allowed
        }
        """

        return


    # ------------------------------------------------------------
    # Сохранение JSON
    # ------------------------------------------------------------
    def save_json(self):
        file_path = filedialog.asksaveasfilename(defaultextension=".json")
        if not file_path:
            return

        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(self.grid_data, f, ensure_ascii=False, indent=4)

        print("JSON сохранён:", file_path)
    
    def save_db(self):
        # Placeholder for database saving logic
        messagebox.showinfo("Сохранение в БД", "Функция сохранения в базу данных пока не реализована.")
    

# ------------------------------------------------------------
# Запуск
# ------------------------------------------------------------
if __name__ == "__main__":  
    root = tk.Tk()
    app = GridAnnotator(root)
    root.mainloop()
