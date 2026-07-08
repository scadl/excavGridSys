import tkinter as tk
from tkinter import filedialog
from PIL import Image, ImageTk
import json

# ============================================================
# Класс GridAnnotator — основной инструмент оцифровки чертежей
# ============================================================
class GridAnnotator:

    def __init__(self, master):
        """
        Конструктор класса.
        Здесь мы создаём окно, холст, кнопки и переменные.
        """

        # Главное окно Tkinter
        self.master = master
        self.master.title("Оцифровка чертежа — Grid Annotator")

        # ------------------------------
        # Переменные для изображения
        # ------------------------------
        self.image = None          # объект PIL.Image
        self.photo = None          # объект ImageTk.PhotoImage для Tkinter

        # ------------------------------
        # Параметры сетки
        # ------------------------------
        self.grid_left = None      # X координата левого верхнего угла сетки
        self.grid_top = None       # Y координата левого верхнего угла сетки

        self.cell_width = None     # ширина клетки (в пикселях)
        self.cell_height = None    # высота клетки (в пикселях)

        # Диапазоны букв и цифр
        self.letters = []
        self.numbers = []

        # ------------------------------
        # Данные квадратов
        # ------------------------------
        # Формат:
        # {
        #   "A1": {"layer": "материк", "allowed": False},
        #   "A2": {"layer": "1", "allowed": True}
        # }
        self.grid_data = {}

        # ------------------------------
        # Этапы кликов
        # ------------------------------
        self.click_stage = 0       # 0 — работа, 1 — первый клик, 2 — второй клик

        # ------------------------------
        # Холст Tkinter
        # ------------------------------
        # Canvas — область, где можно рисовать, отображать изображения,
        # перехватывать клики мыши.
        self.canvas = tk.Canvas(master, width=800, height=600)
        self.canvas.pack()

        # Привязываем обработчик кликов мыши
        self.canvas.bind("<Button-1>", self.on_click)

        # ------------------------------
        # Кнопки управления
        # ------------------------------
        tk.Button(master, text="Загрузить изображение", command=self.load_image).pack()
        tk.Button(master, text="Начать калибровку сетки", command=self.start_calibration).pack()
        tk.Button(master, text="Сохранить JSON", command=self.save_json).pack()

    # ============================================================
    # Загрузка изображения
    # ============================================================
    def load_image(self):
        file_path = filedialog.askopenfilename()
        if not file_path:
            return

        # Загружаем оригинальное изображение
        self.image = Image.open(file_path)

        # Размер окна (можно менять)
        max_width, max_height = 1000, 800

        # Определяем коэффициент масштабирования
        img_width, img_height = self.image.size
        scale = min(max_width / img_width, max_height / img_height, 1.0)

        # Масштабируем изображение (если оно больше окна)
        new_width = int(img_width * scale)
        new_height = int(img_height * scale)
        resized_image = self.image.resize((new_width, new_height), Image.LANCZOS)

        # Сохраняем коэффициент для пересчёта координат
        self.scale = scale

        # Преобразуем для Tkinter
        self.photo = ImageTk.PhotoImage(resized_image)

        # Настраиваем холст под уменьшенное изображение
        self.canvas.config(width=new_width, height=new_height)

        # Отображаем картинку
        self.canvas.create_image(0, 0, anchor="nw", image=self.photo)


    # ============================================================
    # Начало калибровки сетки
    # ============================================================
    def start_calibration(self):
        """
        Пользователь должен сделать два клика:
        1) Левый верхний угол сетки
        2) Правый нижний угол квадрата A1
        """

        print("Кликните ЛЕВЫЙ ВЕРХНИЙ угол сетки.")
        self.click_stage = 1

    # ============================================================
    # Обработка кликов мыши
    # ============================================================
    def on_click(self, event):
        """
        Обрабатывает клики мыши.
        event.x, event.y — координаты клика на Canvas.
        """

        # ------------------------------------------------------------
        # Этап 1 — пользователь кликает левый верхний угол сетки
        # ------------------------------------------------------------
        if self.click_stage == 1:
            print("Левый верхний угол сетки записан.")
            self.grid_left = event.x
            self.grid_top = event.y

            print("Теперь кликните ПРИМЕРНО правый нижний угол квадрата A1.")
            self.click_stage = 2
            return

        # ------------------------------------------------------------
        # Этап 2 — пользователь кликает правый нижний угол A1
        # ------------------------------------------------------------
        if self.click_stage == 2:
            print("Правый нижний угол A1 записан.")

            # dx, dy — вектор между кликами
            dx = event.x - self.grid_left
            dy = event.y - self.grid_top

            # ------------------------------------------------------------
            # Автоматическая коррекция через диагональ под 45°
            # ------------------------------------------------------------
            # Длина диагонали:
            # d = sqrt(dx^2 + dy^2)
            d = (dx**2 + dy**2)**0.5

            # Размер клетки:
            # cell_size = d / sqrt(2)
            cell_size = round(d / (2**0.5))

            self.cell_width = cell_size
            self.cell_height = cell_size

            print(f"Размер клетки (автокоррекция): {cell_size} × {cell_size} пикселей.")

            # ------------------------------------------------------------
            # Запрашиваем диапазоны букв и цифр
            # ------------------------------------------------------------
            letters_range = input("Введите диапазон букв (например A-H): ")
            numbers_range = input("Введите диапазон цифр (например 1-20): ")

            start_letter, end_letter = letters_range.split("-")
            self.letters = [chr(i) for i in range(ord(start_letter), ord(end_letter) + 1)]

            start_num, end_num = numbers_range.split("-")
            self.numbers = list(range(int(start_num), int(end_num) + 1))

            # Рисуем сетку
            self.draw_grid()

            print("Калибровка завершена.")
            self.click_stage = 0
            return

        # ------------------------------------------------------------
        # Этап 0 — пользователь выбирает квадраты
        # ------------------------------------------------------------
        if self.click_stage == 0 and self.cell_width is not None:

            # Перебираем все квадраты
            for i, letter in enumerate(self.letters):
                for j, number in enumerate(self.numbers):

                    # Вычисляем координаты квадрата
                    x1 = self.grid_left + i * self.cell_width
                    y1 = self.grid_top + j * self.cell_height
                    x2 = x1 + self.cell_width
                    y2 = y1 + self.cell_height

                    # Проверяем попадание клика
                    if x1 <= event.x <= x2 and y1 <= event.y <= y2:

                        square_name = f"{letter}{number}"
                        print(f"Вы выбрали квадрат: {square_name}")

                        layer = input("Введите слой (например 1, 2, материк): ")
                        allowed = input("Можно использовать? (yes/no): ").lower() == "yes"

                        # Сохраняем данные
                        self.grid_data[square_name] = {
                            "layer": layer,
                            "allowed": allowed
                        }

                        # Подсветка выбранного квадрата
                        self.canvas.create_rectangle(x1, y1, x2, y2, outline="green", width=3)
                        return

    # ============================================================
    # Рисование сетки
    # ============================================================
    def draw_grid(self):
        """
        Рисует сетку поверх изображения.
        Canvas.create_rectangle — рисует прямоугольник.
        Canvas.create_text — рисует текст.
        """

        for i, letter in enumerate(self.letters):
            for j, number in enumerate(self.numbers):

                x1 = self.grid_left + i * self.cell_width
                y1 = self.grid_top + j * self.cell_height
                x2 = x1 + self.cell_width
                y2 = y1 + self.cell_height

                # Красная рамка квадрата
                self.canvas.create_rectangle(x1, y1, x2, y2, outline="red")

                # Подпись квадрата
                self.canvas.create_text(
                    x1 + 5, y1 + 5,
                    anchor="nw",
                    text=f"{letter}{number}",
                    fill="blue"
                )

    # ============================================================
    # Сохранение JSON
    # ============================================================
    def save_json(self):
        """
        Сохраняет данные квадратов в JSON-файл.
        json.dump — стандартный метод сериализации словаря в JSON.
        """

        file_path = filedialog.asksaveasfilename(defaultextension=".json")
        if not file_path:
            return

        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(self.grid_data, f, ensure_ascii=False, indent=4)

        print("JSON сохранён:", file_path)


# ============================================================
# Запуск программы
# ============================================================
if __name__ == "__main__":
    root = tk.Tk()
    app = GridAnnotator(root)
    root.mainloop()
