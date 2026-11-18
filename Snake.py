import pygame as pygame
import random
import sys
import json
import os
import math

# ==========================================
# 1. INICIALIZACIÓN Y CONFIGURACIÓN GLOBAL
# ==========================================
pygame.init()

# Dimensiones de la ventana principal y tamaño de celda en píxeles
ANCHO_VENTANA, ALTO_VENTANA = 640, 640
TAMANIO_BLOQUE = 20

# Creación de la ventana y título
VENTANA = pygame.display.set_mode((ANCHO_VENTANA, ALTO_VENTANA))
pygame.display.set_caption("Snake - Edición Nokia 3310 (Con Récords)")

# Reloj maestro fijado a 60 FPS para animaciones e interfaz fluidas
RELOJ = pygame.time.Clock()
FPS_RENDER = 60

# Paleta de colores monocromática clásica estilo Nokia LCD
COLOR_FONDO_EXT = (20, 35, 20)        # Carcasa exterior del teléfono
COLOR_PANTALLA_FONDO = (155, 188, 15) # Fondo verde fósforo LCD
COLOR_NOKIA_OSCURO = (15, 56, 15)     # Píxeles activos (serpiente, comida, textos)
COLOR_NOKIA_MEDIO = (48, 98, 48)      # Detalles secundarios y etiquetas


# ==========================================
# 2. CLASE GESTOR DE PUNTUACIÓN (PERSISTENCIA)
# ==========================================
class GestorPuntuacion:
    def __init__(self, archivo="highscore_nokia.json"):
        # Guarda el archivo en el mismo directorio donde se ejecuta el script
        directorio_base = os.path.dirname(os.path.abspath(__file__))
        self.ruta_archivo = os.path.join(directorio_base, archivo)
        self.high_score = self.cargar_record()

    def cargar_record(self):
        # Lee el archivo JSON si existe; si no existe o está corrupto, devuelve 0
        if os.path.exists(self.ruta_archivo):
            try:
                with open(self.ruta_archivo, "r", encoding="utf-8") as f:
                    datos = json.load(f)
                    return int(datos.get("high_score", 0))
            except (json.JSONDecodeError, ValueError, IOError):
                return 0
        return 0

    def guardar_record(self, nuevo_record):
        # Escribe el nuevo récord en el archivo JSON local
        self.high_score = nuevo_record
        try:
            with open(self.ruta_archivo, "w", encoding="utf-8") as f:
                json.dump({"high_score": self.high_score}, f, indent=4)
        except IOError:
            pass

    def evaluar_puntaje(self, puntaje_actual):
        # Compara el puntaje obtenido al perder contra el récord histórico.
        # Retorna True si se estableció un nuevo récord, False en caso contrario.
        if puntaje_actual > self.high_score:
            self.guardar_record(puntaje_actual)
            return True
        return False


# ==========================================
# 3. CLASE SERPIENTE (LÓGICA Y MOVIMIENTO)
# ==========================================
class Serpiente:
    def __init__(self, x_inicial, y_inicial):
        self.cuerpo = [
            {"x": x_inicial, "y": y_inicial},
            {"x": x_inicial - TAMANIO_BLOQUE, "y": y_inicial},
            {"x": x_inicial - (TAMANIO_BLOQUE * 2), "y": y_inicial}
        ]
        self.direccion_x = TAMANIO_BLOQUE
        self.direccion_y = 0
        self.nueva_direccion_aplicada = True

    def cambiar_direccion(self, dx, dy):
        # Evita giros suicidas de 180 grados en un mismo paso lógico
        if self.nueva_direccion_aplicada:
            if dx != 0 and self.direccion_x == 0:
                self.direccion_x = dx
                self.direccion_y = 0
                self.nueva_direccion_aplicada = False
            elif dy != 0 and self.direccion_y == 0:
                self.direccion_x = 0
                self.direccion_y = dy
                self.nueva_direccion_aplicada = False

    def mover(self, atravesar_paredes, area_juego):
        min_x, min_y, max_x, max_y = area_juego
        cabeza_actual = self.cuerpo[0]
        nuevo_x = cabeza_actual["x"] + self.direccion_x
        nuevo_y = cabeza_actual["y"] + self.direccion_y

        # Teletransporte al extremo opuesto si está activo el Modo Fantasma
        if atravesar_paredes:
            if nuevo_x < min_x:
                nuevo_x = max_x - TAMANIO_BLOQUE
            elif nuevo_x >= max_x:
                nuevo_x = min_x
            if nuevo_y < min_y:
                nuevo_y = max_y - TAMANIO_BLOQUE
            elif nuevo_y >= max_y:
                nuevo_y = min_y

        nueva_cabeza = {"x": nuevo_x, "y": nuevo_y}
        self.cuerpo.insert(0, nueva_cabeza)
        self.cuerpo.pop()
        self.nueva_direccion_aplicada = True

    def crecer(self):
        ultimo_segmento = self.cuerpo[-1].copy()
        self.cuerpo.append(ultimo_segmento)

    def colisiona_con_sigo_misma(self):
        cabeza = self.cuerpo[0]
        for segmento in self.cuerpo[1:]:
            if cabeza["x"] == segmento["x"] and cabeza["y"] == segmento["y"]:
                return True
        return False

    def colisiona_con_paredes(self, area_juego):
        min_x, min_y, max_x, max_y = area_juego
        cabeza = self.cuerpo[0]
        return cabeza["x"] < min_x or cabeza["x"] >= max_x or cabeza["y"] < min_y or cabeza["y"] >= max_y

    def dibujar(self, superficie):
        for i, segmento in enumerate(self.cuerpo):
            rect = pygame.Rect(segmento["x"] + 1, segmento["y"] + 1, TAMANIO_BLOQUE - 2, TAMANIO_BLOQUE - 2)
            pygame.draw.rect(superficie, COLOR_NOKIA_OSCURO, rect)

            # Detalle ocular en la cabeza para mayor definición visual
            if i == 0:
                centro_x = segmento["x"] + TAMANIO_BLOQUE // 2
                centro_y = segmento["y"] + TAMANIO_BLOQUE // 2
                pygame.draw.circle(superficie, COLOR_PANTALLA_FONDO, (centro_x, centro_y), 3)


# ==========================================
# 4. CLASE COMIDA (CON ANIMACIÓN DE PULSO)
# ==========================================
class Comida:
    def __init__(self, area_juego, tam_bloque):
        self.min_x, self.min_y, self.max_x, self.max_y = area_juego
        self.tam_bloque = tam_bloque
        self.x = 0
        self.y = 0
        self.generar_nueva_posicion([])

    def generar_nueva_posicion(self, cuerpo_serpiente):
        while True:
            self.x = random.randrange(self.min_x, self.max_x, self.tam_bloque)
            self.y = random.randrange(self.min_y, self.max_y, self.tam_bloque)
            colisiona = any(seg["x"] == self.x and seg["y"] == self.y for seg in cuerpo_serpiente)
            if not colisiona:
                break

    def dibujar(self, superficie, tiempo_ms):
        # Animación suave de latido usando función seno a 60 FPS
        pulso = int(math.sin(tiempo_ms * 0.008) * 1.8)
        margen = max(2, 4 - pulso)
        rect = pygame.Rect(
            self.x + margen,
            self.y + margen,
            self.tam_bloque - (margen * 2),
            self.tam_bloque - (margen * 2)
        )
        pygame.draw.rect(superficie, COLOR_NOKIA_OSCURO, rect, border_radius=4)


# ==========================================
# 5. CLASE JUEGO (MÁQUINA DE ESTADOS Y UI)
# ==========================================
class Juego:
    def __init__(self):
        self.estado_actual = "MENU"
        self.modo_atravesar_paredes = False

        # Intervalo en milisegundos entre pasos de la serpiente (menor = más rápido)
        # 160 ms (~6 pasos/s), 110 ms (~9 pasos/s), 70 ms (~14 pasos/s)
        self.intervalo_movimiento_ms = 110
        self.ultimo_movimiento_ms = 0

        # Área jugable dentro de la pantalla LCD (min_x, min_y, max_x, max_y)
        self.area_juego = (40, 80, 600, 560)

        # Gestor de récord persistente
        self.gestor_puntuacion = GestorPuntuacion()
        self.es_nuevo_record = False

        # Opciones de los menús
        self.opcion_menu_seleccionada = 0
        self.opciones_menu = ["Jugar", "Modo de Juego", "Opciones", "Salir"]

        self.opcion_modo_seleccionada = 0
        self.opciones_modo = ["Clásico (Paredes Mortales)", "Fantasma (Atraviesa Paredes)"]

        self.opcion_opciones_seleccionada = 0
        self.opciones_config = [
            "Velocidad: Lenta",
            "Velocidad: Normal",
            "Velocidad: Frenética",
            "Volver al Menú"
        ]

        # Tipografías estilo retro digital
        self.fuente_titulo = pygame.font.SysFont("Courier New", 28, bold=True)
        self.fuente_subtitulo = pygame.font.SysFont("Courier New", 20, bold=True)
        self.fuente_texto = pygame.font.SysFont("Courier New", 17, bold=True)
        self.fuente_chica = pygame.font.SysFont("Courier New", 14, bold=True)

        self.serpiente = None
        self.comida = None
        self.puntuacion = 0

    def iniciar_partida(self):
        self.serpiente = Serpiente(160, 240)
        self.comida = Comida(self.area_juego, TAMANIO_BLOQUE)
        self.puntuacion = 0
        self.es_nuevo_record = False
        self.ultimo_movimiento_ms = pygame.time.get_ticks()
        self.estado_actual = "JUGANDO"

    def ejecutar(self):
        while True:
            tiempo_actual = pygame.time.get_ticks()
            self.gestionar_eventos()
            self.actualizar_logica(tiempo_actual)
            self.renderizar(tiempo_actual)
            RELOJ.tick(FPS_RENDER)

    def gestionar_eventos(self):
        for evento in pygame.event.get():
            if evento.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            if evento.type == pygame.KEYDOWN:
                if self.estado_actual == "MENU":
                    if evento.key in (pygame.K_UP, pygame.K_w):
                        self.opcion_menu_seleccionada = (self.opcion_menu_seleccionada - 1) % len(self.opciones_menu)
                    elif evento.key in (pygame.K_DOWN, pygame.K_s):
                        self.opcion_menu_seleccionada = (self.opcion_menu_seleccionada + 1) % len(self.opciones_menu)
                    elif evento.key in (pygame.K_RETURN, pygame.K_SPACE):
                        self.ejecutar_accion_menu(self.opcion_menu_seleccionada)

                elif self.estado_actual == "MODOS":
                    if evento.key in (pygame.K_UP, pygame.K_w, pygame.K_DOWN, pygame.K_s):
                        self.opcion_modo_seleccionada = 1 - self.opcion_modo_seleccionada
                    elif evento.key in (pygame.K_RETURN, pygame.K_SPACE):
                        self.modo_atravesar_paredes = (self.opcion_modo_seleccionada == 1)
                        self.estado_actual = "MENU"
                    elif evento.key == pygame.K_ESCAPE:
                        self.estado_actual = "MENU"

                elif self.estado_actual == "OPCIONES":
                    if evento.key in (pygame.K_UP, pygame.K_w):
                        self.opcion_opciones_seleccionada = (self.opcion_opciones_seleccionada - 1) % len(self.opciones_config)
                    elif evento.key in (pygame.K_DOWN, pygame.K_s):
                        self.opcion_opciones_seleccionada = (self.opcion_opciones_seleccionada + 1) % len(self.opciones_config)
                    elif evento.key in (pygame.K_RETURN, pygame.K_SPACE):
                        self.ejecutar_accion_opciones(self.opcion_opciones_seleccionada)
                    elif evento.key == pygame.K_ESCAPE:
                        self.estado_actual = "MENU"

                elif self.estado_actual == "JUGANDO":
                    if evento.key in (pygame.K_LEFT, pygame.K_a):
                        self.serpiente.cambiar_direccion(-TAMANIO_BLOQUE, 0)
                    elif evento.key in (pygame.K_RIGHT, pygame.K_d):
                        self.serpiente.cambiar_direccion(TAMANIO_BLOQUE, 0)
                    elif evento.key in (pygame.K_UP, pygame.K_w):
                        self.serpiente.cambiar_direccion(0, -TAMANIO_BLOQUE)
                    elif evento.key in (pygame.K_DOWN, pygame.K_s):
                        self.serpiente.cambiar_direccion(0, TAMANIO_BLOQUE)
                    elif evento.key == pygame.K_ESCAPE:
                        self.estado_actual = "MENU"

                elif self.estado_actual == "GAME_OVER":
                    if evento.key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_r):
                        self.iniciar_partida()
                    elif evento.key == pygame.K_ESCAPE:
                        self.estado_actual = "MENU"

    def ejecutar_accion_menu(self, indice):
        if indice == 0:
            self.iniciar_partida()
        elif indice == 1:
            self.estado_actual = "MODOS"
        elif indice == 2:
            self.estado_actual = "OPCIONES"
        elif indice == 3:
            pygame.quit()
            sys.exit()

    def ejecutar_accion_opciones(self, indice):
        if indice == 0:
            self.intervalo_movimiento_ms = 160  # Lenta
            self.estado_actual = "MENU"
        elif indice == 1:
            self.intervalo_movimiento_ms = 110  # Normal
            self.estado_actual = "MENU"
        elif indice == 2:
            self.intervalo_movimiento_ms = 70   # Frenética
            self.estado_actual = "MENU"
        elif indice == 3:
            self.estado_actual = "MENU"

    def actualizar_logica(self, tiempo_actual):
        if self.estado_actual == "JUGANDO":
            # Ejecuta el paso de movimiento solo cuando transcurre el intervalo configurado
            if tiempo_actual - self.ultimo_movimiento_ms >= self.intervalo_movimiento_ms:
                self.ultimo_movimiento_ms = tiempo_actual
                self.serpiente.mover(self.modo_atravesar_paredes, self.area_juego)

                # Verifica si come
                cabeza = self.serpiente.cuerpo[0]
                if cabeza["x"] == self.comida.x and cabeza["y"] == self.comida.y:
                    self.serpiente.crecer()
                    self.puntuacion += 10
                    self.comida.generar_nueva_posicion(self.serpiente.cuerpo)

                # Verifica colisiones mortales
                choca_paredes = not self.modo_atravesar_paredes and self.serpiente.colisiona_con_paredes(self.area_juego)
                choca_cuerpo = self.serpiente.colisiona_con_sigo_misma()

                if choca_paredes or choca_cuerpo:
                    # Compara el puntaje final de la partida contra el récord histórico
                    self.es_nuevo_record = self.gestor_puntuacion.evaluar_puntaje(self.puntuacion)
                    self.estado_actual = "GAME_OVER"

    def renderizar(self, tiempo_actual):
        # 1. Carcasa exterior Nokia
        VENTANA.fill(COLOR_FONDO_EXT)

        # 2. Pantalla LCD interna limpia (sin cuadrícula)
        rect_pantalla = pygame.Rect(40, 50, 560, 540)
        pygame.draw.rect(VENTANA, COLOR_PANTALLA_FONDO, rect_pantalla)
        pygame.draw.rect(VENTANA, COLOR_NOKIA_OSCURO, rect_pantalla, 4)

        # Barra superior de estado LCD
        pygame.draw.line(VENTANA, COLOR_NOKIA_OSCURO, (40, 80), (600, 80), 2)

        if self.estado_actual in ["JUGANDO", "GAME_OVER"]:
            # Barra superior con Puntaje actual, Récord y Modo activo
            texto_score = self.fuente_chica.render(f"PTS:{self.puntuacion}", True, COLOR_NOKIA_OSCURO)
            texto_best = self.fuente_chica.render(f"MAX:{self.gestor_puntuacion.high_score}", True, COLOR_NOKIA_OSCURO)
            modo_txt = "FANTASMA" if self.modo_atravesar_paredes else "CLASICO"
            texto_modo = self.fuente_chica.render(modo_txt, True, COLOR_NOKIA_MEDIO)

            VENTANA.blit(texto_score, (55, 58))
            VENTANA.blit(texto_best, (265, 58))
            VENTANA.blit(texto_modo, (510, 58))

            # Renderizado de entidades
            self.comida.dibujar(VENTANA, tiempo_actual)
            self.serpiente.dibujar(VENTANA)

            # Cuadro modal comparativo de Game Over
            if self.estado_actual == "GAME_OVER":
                cuadro_go = pygame.Rect(100, 185, 440, 270)
                pygame.draw.rect(VENTANA, COLOR_PANTALLA_FONDO, cuadro_go)
                pygame.draw.rect(VENTANA, COLOR_NOKIA_OSCURO, cuadro_go, 4)
                pygame.draw.rect(VENTANA, COLOR_NOKIA_OSCURO, cuadro_go.inflate(-10, -10), 1)

                t_go = self.fuente_titulo.render("GAME OVER", True, COLOR_NOKIA_OSCURO)
                VENTANA.blit(t_go, t_go.get_rect(center=(320, 222)))

                # Comparación de puntaje actual vs récord histórico
                t_pts = self.fuente_texto.render(f"PUNTAJE PARTIDA: {self.puntuacion}", True, COLOR_NOKIA_OSCURO)
                t_rec = self.fuente_texto.render(f"RECORD MAXIMO:   {self.gestor_puntuacion.high_score}", True, COLOR_NOKIA_OSCURO)
                VENTANA.blit(t_pts, t_pts.get_rect(center=(320, 268)))
                VENTANA.blit(t_rec, t_rec.get_rect(center=(320, 298)))

                # Mensaje dinámico según el resultado de la comparación
                if self.es_nuevo_record:
                    # Parpadeo retro cada 350 ms para celebrar el nuevo récord
                    if (tiempo_actual // 350) % 2 == 0:
                        caja_rec = pygame.Rect(150, 325, 340, 32)
                        pygame.draw.rect(VENTANA, COLOR_NOKIA_OSCURO, caja_rec)
                        t_msg = self.fuente_texto.render("¡NUEVO RECORD!", True, COLOR_PANTALLA_FONDO)
                        VENTANA.blit(t_msg, t_msg.get_rect(center=(320, 341)))
                else:
                    diferencia = self.gestor_puntuacion.high_score - self.puntuacion
                    msg_dif = f"A {diferencia} PTS DEL RECORD" if diferencia > 0 else "¡EMPATASTE EL RECORD!"
                    t_msg = self.fuente_chica.render(msg_dif, True, COLOR_NOKIA_MEDIO)
                    VENTANA.blit(t_msg, t_msg.get_rect(center=(320, 341)))

                # Instrucciones inferiores
                t_sub1 = self.fuente_chica.render("ENTER: JUGAR DE NUEVO", True, COLOR_NOKIA_OSCURO)
                t_sub2 = self.fuente_chica.render("ESC:   MENU PRINCIPAL", True, COLOR_NOKIA_OSCURO)
                VENTANA.blit(t_sub1, t_sub1.get_rect(center=(320, 392)))
                VENTANA.blit(t_sub2, t_sub2.get_rect(center=(320, 418)))

        elif self.estado_actual == "MENU":
            self.dibujar_menu("NOKIA SNAKE", self.opciones_menu, self.opcion_menu_seleccionada)
            # Muestra el récord actual en la parte inferior del menú principal
            t_best_menu = self.fuente_chica.render(
                f"RECORD ACTUAL: {self.gestor_puntuacion.high_score} PTS",
                True,
                COLOR_NOKIA_MEDIO
            )
            VENTANA.blit(t_best_menu, t_best_menu.get_rect(center=(320, 535)))

        elif self.estado_actual == "MODOS":
            self.dibujar_menu("SELECCIONAR MODO", self.opciones_modo, self.opcion_modo_seleccionada)

        elif self.estado_actual == "OPCIONES":
            self.dibujar_menu("CONFIGURACION", self.opciones_config, self.opcion_opciones_seleccionada)

        # Grabado inferior de carcasa
        marca_nokia = self.fuente_chica.render("NOKIA - 3310", True, (90, 110, 90))
        VENTANA.blit(marca_nokia, marca_nokia.get_rect(center=(320, 615)))

        pygame.display.flip()

    def dibujar_menu(self, titulo, opciones, seleccion):
        t_titulo = self.fuente_titulo.render(titulo, True, COLOR_NOKIA_OSCURO)
        VENTANA.blit(t_titulo, t_titulo.get_rect(center=(320, 135)))

        for i, opcion in enumerate(opciones):
            centro_y = 225 + (i * 58)

            if i == seleccion:
                ancho_caja, alto_caja = 380, 40
                rect_sel = pygame.Rect(320 - ancho_caja // 2, centro_y - alto_caja // 2, ancho_caja, alto_caja)
                pygame.draw.rect(VENTANA, COLOR_NOKIA_OSCURO, rect_sel)
                texto_opcion = self.fuente_texto.render(f"> {opcion}", True, COLOR_PANTALLA_FONDO)
            else:
                texto_opcion = self.fuente_texto.render(f"  {opcion}", True, COLOR_NOKIA_OSCURO)

            VENTANA.blit(texto_opcion, texto_opcion.get_rect(center=(320, centro_y)))


# ==========================================
# 6. PUNTO DE ENTRADA PRINCIPAL
# ==========================================
if __name__ == "__main__":
    juego = Juego()
    juego.ejecutar()