from fpdf import FPDF
from datetime import datetime
from pathlib import Path
import os

# --- PALETA DE COLORES DE MARCA (RGB) ---
BRAND_DARK_GREEN = (79, 159, 74)    # #4F9F4A
BRAND_ORANGE = (246, 106, 35)       # #F66A23
BRAND_RED = (217, 55, 37)           # #D93725
BRAND_DARK_GREY = (50, 50, 50)      # #323232
HEADER_BG_GREY = (245, 245, 245)

# --- ACTUALIZACIÓN DE RUTA ---
# Buscamos en la carpeta 'branding' desde la raíz del proyecto
LOGO_PATH = Path("branding/logo.png")

class FireReportPDF(FPDF):
    def header(self):
        # 1. Fondo
        self.set_fill_color(*HEADER_BG_GREY)
        self.rect(0, 0, 210, 45, 'F')
        
        # 2. Insertar Logo
        if LOGO_PATH.exists():
            # Ajustamos un poco la posición para que quede centrado verticalmente en el header
            self.image(str(LOGO_PATH), x=10, y=8, w=28)
            text_x_offset = 42
        else:
            # Fallback por si no encuentra la imagen (para no romper el PDF)
            text_x_offset = 10 

        # 3. Título
        self.set_xy(text_x_offset, 12)
        self.set_font('Helvetica', 'B', 20)
        self.set_text_color(*BRAND_DARK_GREEN)
        self.cell(0, 10, 'Reporte de Recuperación Post-Incendio', align='L')
        
        # 4. Subtítulo
        self.set_xy(text_x_offset, 22)
        self.set_font('Helvetica', '', 10)
        self.set_text_color(*BRAND_DARK_GREY)
        fecha_actual = datetime.now().strftime("%d/%m/%Y")
        self.cell(0, 10, f'Generado el {fecha_actual} | Wildfire Recovery Argentina', align='L')
        
        self.set_y(50)

    def footer(self):
        self.set_y(-15)
        self.set_font('Helvetica', 'I', 8)
        self.set_text_color(*BRAND_DARK_GREY)
        self.cell(0, 10, f'Página {self.page_no()}/{{nb}} | Datos satelitales provistos por NASA FIRMS & Sentinel-2', align='C')

class ReportGenerator:
    def __init__(self, output_folder: Path):
        self.output_folder = output_folder
        self.output_folder.mkdir(parents=True, exist_ok=True)

    def generate_pdf(self, incendio_data: dict, image_path: Path, output_filename: str) -> Path:
        pdf = FireReportPDF()
        pdf.alias_nb_pages()
        pdf.add_page()
        pdf.set_auto_page_break(auto=True, margin=15)

        # --- SECCIÓN 1: DATOS CLAVE ---
        pdf.set_font('Helvetica', 'B', 14)
        pdf.set_text_color(*BRAND_ORANGE)
        pdf.cell(0, 10, '1. Detalles del Evento', new_x="LMARGIN", new_y="NEXT")
        
        pdf.set_draw_color(*BRAND_ORANGE)
        pdf.set_line_width(0.5)
        pdf.line(10, pdf.get_y(), 200, pdf.get_y())
        pdf.ln(5)

        def row(label, value, value_color=BRAND_DARK_GREY, is_bold_value=False):
            pdf.set_font('Helvetica', 'B', 10)
            pdf.set_text_color(*BRAND_DARK_GREY)
            pdf.cell(50, 7, label, border=0)
            
            font_style = 'B' if is_bold_value else ''
            pdf.set_font('Helvetica', font_style, 10)
            pdf.set_text_color(*value_color)
            
            x_pos = pdf.get_x()
            y_pos = pdf.get_y()
            pdf.multi_cell(0, 7, str(value), border=0, align='L')
            if pdf.get_y() > y_pos + 7:
                 pdf.set_y(pdf.get_y())
            else:
                 pdf.set_y(y_pos + 7)
            pdf.set_x(10)

        row("ID del Incendio:", incendio_data.get('id', 'N/A'))
        fecha_fmt = datetime.strptime(str(incendio_data.get('fecha_deteccion')), "%Y-%m-%d").strftime("%d/%m/%Y")
        row("Fecha de Inicio:", fecha_fmt)
        
        ubicacion_str = f"{incendio_data.get('latitud')}, {incendio_data.get('longitud')}"
        row("Coordenadas:", ubicacion_str)

        row("Ubicación:", f"{incendio_data.get('localidad', '')}, {incendio_data.get('provincia', '')}")
        
        row("Tipo de Ecosistema:", incendio_data.get('tipo_suelo', 'No determinado'), value_color=BRAND_DARK_GREEN, is_bold_value=True)
        
        if incendio_data.get('es_area_protegida'):
            row("ÁREA PROTEGIDA:", incendio_data.get('nombre_parque'), value_color=BRAND_RED, is_bold_value=True)
        
        row("Área Afectada:", f"{incendio_data.get('area', 'N/A')} Hectáreas")

        pdf.ln(8)

        # --- SECCIÓN 2: EVIDENCIA VISUAL ---
        pdf.set_font('Helvetica', 'B', 14)
        pdf.set_text_color(*BRAND_ORANGE)
        pdf.cell(0, 10, '2. Evidencia Satelital (Análisis Multiespectral)', new_x="LMARGIN", new_y="NEXT")
        pdf.line(10, pdf.get_y(), 200, pdf.get_y())
        pdf.ln(5)

        pdf.set_font('Helvetica', '', 10)
        pdf.set_text_color(*BRAND_DARK_GREY)
        pdf.multi_cell(0, 5, "La siguiente imagen compara la evolución del terreno utilizando imágenes Sentinel-2 en alta resolución. Se presentan tres vistas: Color Real (RGB), Infrarrojo de Onda Corta (SWIR) para destacar cicatrices de fuego, e Índice de Vegetación (NDVI) para medir la salud de la flora.")
        pdf.ln(5)

        if image_path and image_path.exists():
            pdf.image(str(image_path), x=15, w=180)
        else:
            pdf.set_text_color(*BRAND_RED)
            pdf.cell(0, 10, "Error: No se pudo cargar la imagen satelital.", new_x="LMARGIN", new_y="NEXT")

        # --- SECCIÓN 3: GUÍA ---
        pdf.ln(5)
        if pdf.get_y() > 220:
             pdf.add_page()

        pdf.set_font('Helvetica', 'B', 14)
        pdf.set_text_color(*BRAND_ORANGE)
        pdf.cell(0, 10, '3. Guía de Interpretación', new_x="LMARGIN", new_y="NEXT")
        pdf.line(10, pdf.get_y(), 200, pdf.get_y())
        pdf.ln(5)
        
        pdf.set_font('Helvetica', '', 10)
        pdf.set_text_color(*BRAND_DARK_GREY)
        
        pdf.set_font('Helvetica', 'B', 10)
        pdf.write(5, "Fila Central (SWIR - Detección): ")
        pdf.set_font('Helvetica', '', 10)
        pdf.write(5, "Permite 'ver' a través del humo. Las áreas quemadas recientes aparecen en color marrón oscuro o rojizo brillante, diferenciándose claramente del suelo desnudo no quemado.\n\n")
        
        pdf.set_font('Helvetica', 'B', 10)
        pdf.write(5, "Fila Inferior (NDVI - Salud): ")
        pdf.set_font('Helvetica', '', 10)
        pdf.write(5, "Mide el verdor y densidad de la vegetación. Los tonos verdes indican vegetación sana. Los tonos amarillos, rojos o negros indican vegetación estresada, muerta o ausencia total de biomasa.")

        output_path = self.output_folder / output_filename
        pdf.output(output_path)
        return output_path