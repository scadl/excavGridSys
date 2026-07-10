import tkinter as tk

class DragAndDropExample:
    def __init__(self, root):
        self.canvas = tk.Canvas(root, width=400, height=400, bg='white')
        self.canvas.pack(fill=tk.BOTH, expand=True)

        self.handle = self.canvas.create_rectangle(50, 50, 70, 70, fill='yellow', outline='black', tags='handle')

        self.dragging = None

        self.canvas.tag_bind('handle', '<ButtonPress-1>', self.on_press)
        self.canvas.tag_bind('handle', '<B1-Motion>', self.on_drag)
        self.canvas.tag_bind('handle', '<ButtonRelease-1>', self.on_release)

    def on_press(self, event):
        self.dragging = self.handle
    
    def on_drag(self, event):
        if self.dragging:
            size = 20
            x, y = event.x, event.y
            self.canvas.coords(self.dragging, x, y, x + size, y + size)
    
    def on_release(self, event):
        self.dragging = None

root = tk.Tk()
root.title("Drag and Drop Example")
app = DragAndDropExample(root)
root.mainloop()