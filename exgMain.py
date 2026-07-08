import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, ttk
from PIL import Image, ImageTk
import json

class GridAnnotator:

    def __init__(self, master):
        self.master = master
        self.master.title("Оцифровка чертежа — Canvas")

        # Разрешаем менять размер окна
        self.master.resizable(True, True)

        # Создаём второе окно — панель управления
        self.control_window = tk.Toplevel(self.master)
        self.control_window.title("Панель управления")
        self.control_window.resizable(True, True)

        # Оригинальное изображение
        self.image = None
        self.photo = None
        self.scale = 1.0

        # Параметры сетки
        self.grid_left = None
        self.grid_top = None
        self.cell_width = None
        self.cell_height = None

        self.letters = []
        self.numbers = []
        self.grid_data = {}

        self.click_stage = 0

        # Canvas для чертежа
        self.canvas = tk.Canvas(master, bg="gray")
        self.canvas.pack(fill=tk.BOTH, expand=True)

        # Обработчики
        self.canvas.bind("<Button-1>", self.on_click)
        self.master.bind("<Configure>", self.on_resize)

        # Кнопки — теперь в отдельном окне
        ttk.Button(self.control_window, text="Загрузить изображение", command=self.load_image).pack(fill=tk.X)
        ttk.Button(self.control_window, text="Начать калибровку сетки", command=self.start_calibration).pack(fill=tk.X)
        ttk.Button(self.control_window, text="Сбросить сетку", command=self.reset_grid).pack(fill=tk.X)
        ttk.Button(self.control_window, text="Сохранить JSON", command=self.save_json).pack(fill=tk.X)


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
    def update_scaled_image(self):
        if self.image is None:
            return

        win_w = self.master.winfo_width()
        win_h = self.master.winfo_height()

        img_w, img_h = self.image.size

        self.scale = min(win_w / img_w, win_h / img_h)

        new_w = int(img_w * self.scale)
        new_h = int(img_h * self.scale)

        resized = self.image.resize((new_w, new_h), Image.LANCZOS)
        self.photo = ImageTk.PhotoImage(resized)

        self.canvas.config(width=new_w, height=new_h)
        self.canvas.delete("all")
        self.canvas.create_image(0, 0, anchor="nw", image=self.photo)

        if self.cell_width:
            self.draw_grid()

    # ------------------------------------------------------------
    # Обработка изменения размера окна
    # ------------------------------------------------------------
    def on_resize(self, event):
        self.update_scaled_image()

    # ------------------------------------------------------------
    # Калибровка сетки
    # ------------------------------------------------------------
    def start_calibration(self):
        print("Кликните ЛЕВЫЙ ВЕРХНИЙ угол сетки.")
        self.click_stage = 1

    # ------------------------------------------------------------
    # Обработка кликов
    # ------------------------------------------------------------
    def on_click(self, event):
        orig_x = int(event.x / self.scale)
        orig_y = int(event.y / self.scale)

        if self.click_stage == 1:
            self.grid_left = orig_x
            self.grid_top = orig_y
            print("Теперь кликните ПРИМЕРНО правый нижний угол квадрата A1.")
            self.click_stage = 2
            return

        if self.click_stage == 2:
            dx = orig_x - self.grid_left
            dy = orig_y - self.grid_top

            d = (dx**2 + dy**2)**0.5
            cell_size = round(d / (2**0.5))

            self.cell_width = cell_size
            self.cell_height = cell_size

            print(f"Размер клетки: {cell_size} × {cell_size}")

            letters_range = simpledialog.askstring("Диапазон букв", "Введите диапазон букв (например A-H):")

            numbers_range = simpledialog.askinteger("Диапазон цифр", "Введите количество строк (например 20):")

            start_letter, end_letter = letters_range.split("-")
            letters_raw = [chr(i) for i in range(ord(start_letter), ord(end_letter) + 1)]

            # Исключаем буквы Ё и Й
            self.letters = [L for L in letters_raw if L not in ("Ё", "Й")]

            start_num = 1
            end_num = numbers_range
            self.numbers = list(range(int(start_num), int(end_num) + 1))

            self.draw_grid()
            self.click_stage = 0
            return

        if self.click_stage == 0 and self.cell_width:

            for i, letter in enumerate(self.letters):
                for j, number in enumerate(self.numbers):

                    x1 = self.grid_left + i * self.cell_width
                    y1 = self.grid_top + j * self.cell_height
                    x2 = x1 + self.cell_width
                    y2 = y1 + self.cell_height

                    if x1 <= orig_x <= x2 and y1 <= orig_y <= y2:
                        square_name = f"{letter}{number}"
                        print(f"Вы выбрали квадрат: {square_name}")

                        
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

                        sx1 = int(x1 * self.scale)
                        sy1 = int(y1 * self.scale)
                        sx2 = int(x2 * self.scale)
                        sy2 = int(y2 * self.scale)

                        self.canvas.create_rectangle(sx1, sy1, sx2, sy2, outline="green", width=3)
                        return

    # ------------------------------------------------------------
    # Рисование сетки
    # ------------------------------------------------------------
    def draw_grid(self):
        for i, letter in enumerate(self.letters):
            for j, number in enumerate(self.numbers):

                x1 = self.grid_left + i * self.cell_width
                y1 = self.grid_top + j * self.cell_height
                x2 = x1 + self.cell_width
                y2 = y1 + self.cell_height

                sx1 = int(x1 * self.scale)
                sy1 = int(y1 * self.scale)
                sx2 = int(x2 * self.scale)
                sy2 = int(y2 * self.scale)

                self.canvas.create_rectangle(sx1, sy1, sx2, sy2, outline="red")
                self.canvas.create_text(sx1 + 5, sy1 + 5, anchor="nw",
                                        text=f"{letter}{number}", fill="blue")

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
    
    # ------------------------------------------------------------
    # Полный сброс сетки и данных.
    # ------------------------------------------------------------   
    def reset_grid(self):

        self.grid_left = None
        self.grid_top = None
        self.cell_width = None
        self.cell_height = None

        self.letters = []
        self.numbers = []
        self.grid_data = {}

        self.click_stage = 0

        # Очищаем Canvas
        self.canvas.delete("all")

        # Перерисовываем изображение, если оно загружено
        if self.photo:
            self.canvas.create_image(0, 0, anchor="nw", image=self.photo)

        print("Сетка сброшена. Можно начать калибровку заново.")

# ------------------------------------------------------------
# Запуск
# ------------------------------------------------------------
if __name__ == "__main__":
    root = tk.Tk()
    app = GridAnnotator(root)
    root.mainloop()
