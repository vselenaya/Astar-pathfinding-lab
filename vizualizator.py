import pygame
import time


# === НАСТРОЙКА ЦВЕТОВ КЛЕТОК (цвет = тройка (r, g, b) формата RGB) ===
GREY = (100, 100, 100)  # цвет линии сетки
START = (0, 128, 0)  # старт, финиш, препятствия
GOAL = (255, 0, 0)
OBSTACLE = (180, 226, 180)
CLOSED = (220, 220, 220)  # цвета клеток списков CLOSED и OPEN
OPEN = (255, 214, 140)
PATH = (179, 179, 255)  # клетки пути
DEFAULT = (255, 255, 255)  # цвет обычной (пустой) клетки

UNKNOWN_OBS = (128, 128, 128)  # дополнительно цвета для A* с частичной наблюдаемостью: неизвестные препятствия, 
FIELD_OF_VIEW = (255, 120, 120)  # поле зрения работа
COLLISION = (184, 164, 53)  # коллизия текущего пути с препятствиями (о которых ещё неизвестно)
CUR_POSITION = (0, 0, 255)  # текущая позиция робота




class Cell:
    def __init__(self, i, j, size):
        """
        Инициализируем клетку grid-поля

        Args:
            i (int): номер столбца этой клетки
            j (int): номер строки
            size (int): размер клетки для рисования на экране (длина её стороны в пикселях)
        """
        self.i = i
        self.j = j
        self.size = size
        self.y = i * size  # координаты угла (при условии, что i, j растут сонаправленно y, x) клетки (в пикселях)
        self.x = j * size  # (координаты того из 4-ёх углов клетки, которые наименьшие - в pygame это левый верхний)
        self.reset()  # устанавливаем значения "по умолчанию"


    def reset(self):
        """
        Сбрасываем все настройки клетки до значений по умолчанию
        """
        self.obs = False  # или True: является ли препятствием
        self.initial = None  # или True, False: является ли стартовой (True) или целевой (False) клеткой (None - обычная клетка)
        self.searching = None  # или True, False: принадлежит ли клетка из списка OPEN (True) или CLOSED (False) (None - клетка вне дерева поиска)
        self.path = False  # или True: является ли клетка частью итогового пути
        self.color = None  # или (r, g, b): значение цвета клетки (если он None, вычисляем его исходя их предыдущих параметров)
        

    def set_obstacle(self):
        if self.initial is not None:
            print("Старт/финиш не могут быть препятствием!")
            return False
        self.obs = True
        return True  # возвращаем, что произошел успех (клетка поменяла свой тип)
        
        
    def set_initial(self, start=True):
        if self.obs == True:
           print("Стартом/финишем нельзя выбрать препятствие!")
           return False
        if self.initial is not None:
            print("Клетка уже является стартом/финишем, менять нельзя!")
            return False
        self.initial = start
        return True
        
    
    def set_searching(self, open=True):
        self.searching = open
        return True
    
    
    def set_path(self):
        if self.initial is not None:  # не перезатираем старт финиш путём
            return
        self.path = True

       
    def draw(self, window):
        """
        Функция для рисования клетки на экран через pygame

        Args:
            window (Surface): куда рисовать клетку (некоторое окно от pygame)
        """
        if self.initial == True:  # определяем цвет клетки (важно, что условия именно в таком порядке, так как, например, если клетка = start,
            color = START         # то нам не важны остальные её характеристики (в OPEN она или в CLOSED - не важно) - рисуем её как цвета START) 
        elif self.initial == False:
            color = GOAL
        elif self.path == True:
            color = PATH
        elif self.searching == True:
            color = OPEN
        elif self.searching == False:
            color = CLOSED
        elif self.obs == True:
            color = OBSTACLE
        else:
            color = DEFAULT
        if self.color is not None:  # но если self.color задан, то вне зависимости от параметров, рисуем этот цвет
            color = self.color
        pygame.draw.rect(window, color, (self.x, self.y, self.size, self.size))  # рисуем клетку как прямоугольник size на size пикселей




class GridMap:
    def __init__(self, rows, cols, wHeight, wWidth):
        """
        Создаём grid-карту (поле, таблица из клеток Cell)

        Args:
            rows (int): высота клетчатого поля (в клетках)
            cols (int): его ширина
            wHeight (int): высота окна для рисования (в пикселях)
            wWidth (int): его ширина 
        """
        
        self.rows = rows
        self.cols = cols
        self.size = min(wWidth // cols, wHeight // rows)  # размер клетки (чтобы таблица cols × rows клеток влезла в окно HEIGHT × WIDTH пикселей)
        self.width = self.size * cols  # размер grid (то есть таблицы из клеток Cell) в пикселях на экране
        self.height = self.size * rows
    
        self.cells = []  # массив по [i][j] получает клетку Cell (в отличие от self.bit_grid, где по [i][j] получаем только, занята ли клетка)
        for i in range(rows):  # заполняем двумерный массив self.cells клетками типа Cell
            self.cells.append([])
            for j in range(cols):
                cell = Cell(i, j, self.size)
                self.cells[i].append(cell)
                
        self.start = None  # или (i, j): координаты старта и финиша
        self.goal = None
                
    
    def process_click(self, pos, reset=False):
        """
        Функция обрабатывает клик мышкой по позиции pos (= tuple двух чисел: координат (в пикселях), куда кликнули)

        Args:
            pos (Tuple[int, int]): позиция, где на экране произошёл клик
            reset (bool): нужно ли сбросить параметры клетки при клике на неё
        """
        
        x, y = pos  # в pygame координаты клика = координаты внутри окна (причём ось x слева направо, а ось y сверху вни)
        if (not (0 <= y < self.height)) or (not (0 <= x < self.width)):  # если клик вне таблицы grid, то ничего не делаем (важно, что строгий 
            return                                                       # знак <, так как у номера клеток i, j тоже от 0 до (строго) rows, cols)  
        i = y // self.size  # получаем позицию клетки в grid, куда кликнули
        j = x // self.size
        cell = self.cells[i][j]  # и саму клетку
        
        if reset:  # в случае сброса - удаляем информацию о старте/финише
            if self.start == (i, j):
                self.start = None
            if self.goal == (i, j):
                self.goal = None
            cell.reset()  # очищаем клетку
            return
        
        # по порядку пытаемся сделать клетку стартом, финишем или препятствием:
        if self.start is None:
            if cell.set_initial(True):  # если успешно получилось поменять тип клетки, то запоминаем старт
                self.start = (i, j)
        elif self.goal is None:
            if cell.set_initial(False):
                self.goal = (i, j)
        else:
            cell.set_obstacle()
            

    def draw(self, window):
        """
        Функция рисования grid в виде сетки - просто проводим вертикальные и горизонтальные линии, а также закрашиваем клетки

        Args:
            window (Surface): куда рисуем grid
        """
        assert (self.width <= window.get_width()) and (self.height <= window.get_height()), "Клетчатое поле больше окна для рисования!"
        window.fill((255, 255, 255))  # очищаем окно (заполняем его белым цветом)

        for row in self.cells:  # сначала рисуем клетки (нужным цветом)
            for cell in row:
                cell.draw(window)
 
        for i in range(self.rows+1):  # проводим горизонтальные линии на i-ом ряду
            pygame.draw.line(window, GREY, (0, i * self.size), (self.width, i * self.size))
            for j in range(self.cols+1):  # аналогично вертикальные линии
                pygame.draw.line(window, GREY, (j * self.size, 0), (j * self.size, self.height))
                
                
    def reset(self):
        """
        Функция сбрасывает всю карту до чистого листа
        """
        self.start = None
        self.goal = None
        for i in range(self.rows):
            for j in range(self.cols):
                self.cells[i][j].reset()
        



# ====== Класс, отвечающий за интерактивную симуляцию ======
class Simulator:
    def __init__(self, map,
                 bit_grid, astar_algorithm, 
                 reset_astar, open, closed):
        """
        Создаём симулятор для алгоритма A*
        """
        self.map = map  # карта, экземпляр GridMap
        self.window = None  # окно, куда рисовать (пока его нет)
        self.bit_grid = bit_grid  # таблица из 0 и 1 занятости клеток (в (i,j) стоит 1, если эта клетка от препятствия и 0 в другом случае)
        self.astar_algorithm = astar_algorithm  # ссылка на функцию = реализация A* (сделанная как генератор, через yield!)
        self.reset_astar = reset_astar  # функция сброса всех данных поиска с предыдущего запуска A*
        self.open = open  # ссылки на списки OPEN и CLOSED, используемые A* (они должны быть итерируемыми коллекциями)
        self.closed = closed
        self.frames = []  # кадры окна, куда рисуется картинка (пустой массив кадров изначально) -- эти кадры потом можно превратить в gif
        self.cnt_displays = 0  # счётчик количества отрисовок на экран
        
        
    def display(self, save=False):
        self.map.draw(self.window)  # отрисовываем все клетки в окно window
        pygame.display.update()  # обновляем изображение на экране
        if save:
            frame = pygame.surfarray.array3d(pygame.display.get_surface())  # получаем массив пикселей окна, в формате (X, Y, RGB)
            self.frames.append(frame)  # сохранение текущего кадра
        self.cnt_displays += 1
            
            
    def dump_gif(self, file='output.gif', fps=30, end_pause_sec=1.5):
        """
        Сохраняет кадры в GIF, имя файла file. Частота кадров задаётся параметром fps (1/fps = время одного кадра в секундах).
        Также добавим end_pause_sec: сколько секунд "висеть" на последнем кадре (перед зацикливанием).
        """
        if len(self.frames) == 0:
            print("Нет кадров для сохранения!")
            return
        
        print(f"Обработка {len(self.frames)} кадров...")
        import imageio
        import numpy as np

        processed_frames = []
        for frame in self.frames:
            rotated_frame = np.transpose(frame, (1, 0, 2))  # Поворачиваем: из формата (Width, Height, 3) -> в формат (Height, Width, 3)
            processed_frames.append(rotated_frame)

        if end_pause_sec > 0:
            last_frame = processed_frames[-1]
            # Вычисляем, сколько копий последнего кадра нужно добавить
            # Например: 30 fps * 2 секунды = 60 лишних кадров
            extra_count = int(fps * end_pause_sec)
            processed_frames.extend([last_frame] * extra_count)  # Добавляем копии в конец списка (они почти не увеличиваю размер из-за сжатия)
            print(f"Добавлено {extra_count} статичных кадров для паузы.")

        try:
            imageio.mimsave(file, processed_frames, fps=fps, loop=0)  # loop=0 означает бесконечный повтор gif
            print(f"Готово! Файл сохранен как {file}")
        except Exception as e:
            print(f"Ошибка при сохранении: {e}")
        
        
    def astar_step_update(self, save_frames=False):
        """
        Функция отрисовывает результаты одного шага работы алгоритма A*: изменения списков OPEN и CLOSED.
        """
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                raise Exception("Досрочно закрыли окно!")  # если завершили рисования (например, закрыли окно, гди рисуем), то уведомляем об этом
        for (i, j) in self.open:
            self.map.cells[i][j].set_searching(True)  # обновляем клетки с учётом изменившихся OPEN и CLOSED
        for (i, j) in self.closed:
            self.map.cells[i][j].set_searching(False)
        self.display(save_frames)


    def astar_simulation(self, save_frames=False):
        """
        Функция, которая запускает алгоритм astar и отрисовывает все шаги его выполнения.
        """
        self.reset_astar()  # сбрасываем данные предыдущего поиска перед запуском нового
        for i in range(self.map.rows):
            for j in range(self.map.cols):
                self.bit_grid[i][j] = int(self.map.cells[i][j].obs)  # заполняем значения занятости (1 и 0) клеток согласно GridMap
        gen_path = self.astar_algorithm(*self.map.start, *self.map.goal)  # получаем генератор (на каждой итерации он делает очередной шаг A*)
        try:
            while True: 
                next(gen_path)  # пока можем делаем и отрисовываем шаги A*
                self.astar_step_update(save_frames)
        except StopIteration as e:  # как только алгоритм дошёл до конца (вызвался return), то получаем значение этого return 
            path = e.value          # (он возвращает найденный путь) из StopIteration, который вызывается в генераторе, когда тот дошел до конца
                
        if len(path) == 0:  # если найденный путь - пустой
            print("Путь не найден!")
        else:
            print("Нашли путь!")
            for (i, j) in path:
                self.map.cells[i][j].set_path()
                self.display(save_frames)  # обновляем картинку, рисуя клетки пути по одной 
                
    
    def astar_get_path(self, si, sj, fi, fj):
        """
        Функция, которая полностью проходит генератор и получает весь путь, найденный A*.
        """
        self.reset_astar()  # перед началом сбрасываем поисковые данные (но не bit_grid - он может переиспользоваться с прошлой итерации)
        gen_path = self.astar_algorithm(si, sj, fi, fj)
        try:
            while True:
                next(gen_path)
        except StopIteration as e:
            path = e.value
        return path
    
    
    def partial_observed_astar_simulation(self, R=3, save_frames=False):
        """
        Функция, которая запускает A* с частичной наблюдаемостью - то есть робот знает только о препятствиях, координаты которого
        удалены от его текущей точки <= R единиц.
        """
        ci, cj = self.map.start  # текущее положение робота - изначально старт
        rows = self.map.rows
        cols = self.map.cols
        for i in range(rows):
            for j in range(cols):
                self.bit_grid[i][j] = 0  # изначально роботу неизвестно о препятствиях -> занятость полностью нулевая
                
        while True:
            time.sleep(0.1)  # чтобы выглядело плавнее, засыпаем на 0.1 секунды каждый раз
            for i in range(rows):
                for j in range(cols):
                    if self.map.cells[i][j].obs and abs(ci - i) <= R and abs(cj - j) <= R:  # препятствия, которые попали в зону видимости робота,
                        self.bit_grid[i][j] = 1  # запоминаем (и далее они уже считаются известными, даже если робот проехал дальше)
                        
            for i in range(rows):  # меняем цвета клеток, которые нарисуем (тут в отличие от обычного запуска A* не будет open и closed ->
                for j in range(cols):  # -> цвета чуть иные)
                    if self.map.cells[i][j].initial is not None:  # старт и финиш не трогаем - они будут теми же, что обычно
                        pass
                    elif ci == i and cj == j:  # текущую позицию робота рисуем синим
                        self.map.cells[ci][cj].color = CUR_POSITION
                    elif self.map.cells[i][j].obs:  # препятствия вообще рисуем серым
                        self.map.cells[i][j].color = UNKNOWN_OBS
                    elif abs(ci - i) <= R and abs(cj - j) <= R:  # а свободные клетки в поле зрения робота - красноватым (чтобы был понятен обзор)
                        self.map.cells[i][j].color = FIELD_OF_VIEW
                    else:  # наконец, оставшиеся клетки рисуем белым
                        self.map.cells[i][j].color = DEFAULT           
                    if self.bit_grid[i][j] == 1:  # ! дополнительно клетки препятствий, о которых роботу уже известно рисуем зелёным
                        self.map.cells[i][j].color = OBSTACLE
            
            path = self.astar_get_path(ci, cj, *self.map.goal)  # ищем путь от данной точки
            if len(path) == 0:
                print("Нет пути!")
                break
            elif len(path) == 1:
                print("Мы на месте!")
                break
            else:  # сдвигаемся на один шаг в этом пути и тд
                ci, cj = path[1]
                
            for (i, j) in path[1:-1]:  # рисуем путь (точнее, клетки без первой и последней)
                if self.map.cells[i][j].color == DEFAULT or self.map.cells[i][j].color == FIELD_OF_VIEW:
                    self.map.cells[i][j].color = PATH
                elif self.map.cells[i][j].color == UNKNOWN_OBS:
                    self.map.cells[i][j].color = COLLISION
                    
            self.display(save_frames)  # отрисовываем на экран
    
            
    def run(self, window, save_frames=False, partial_observed=False, R=3):
        """
        Функция запускает интерактивную симуляцию.
        Параметр save_frames указывает, необходимо ли сохранять кадры (чтобы потом можно было вызвать dump_gif() для получения gif-ки),
        параметр partial_observed указывает, хотим ли мы запустить версию с частичной наблюдаемостью (в этом случае имеет смысл параметр R,
        указывающий дальностью обзора робота).
        """
        self.frames.clear()  # очищаем от предыдущих запусков
        self.window = window
        try:
            while True:
                self.display(False)  # обновляем окно
                
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:  # если закрыли окно - выходим просто
                        return
            
                    if pygame.mouse.get_pressed()[0]:  # ЛЕВАЯ кнопка мыши нажата
                        pos = pygame.mouse.get_pos()
                        self.map.process_click(pos)  
                
                    elif pygame.mouse.get_pressed()[2]: # ПРАВАЯ
                        pos = pygame.mouse.get_pos()
                        self.map.process_click(pos, True)
            
                    if event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE:  # по нажатому пробелу начинаем симуляцию
                        if (self.map.start is None) or (self.map.goal is None):
                            print("Не заданы старт или финиш !")
                            continue
                        if partial_observed:
                            self.partial_observed_astar_simulation(R, save_frames=save_frames)  # тут частичная наблюдаемость
                        else:
                            self.astar_simulation(save_frames=save_frames)  # а тут запускаем обычный симулятор
                        
                    if event.type == pygame.KEYDOWN and event.key == pygame.K_c:  # сбрасываем карту до чистого листа
                        self.map.reset()
        finally:  # в случае любых ошибок, закрываем окно
            pygame.quit()       
    