# Tabla de simbolos por ambiente para mini-Pascal.
#
# Cada instancia representa un ambiente lexico: posee una tabla hash propia, un
# enlace al ambiente exterior y una lista de ambientes hijos. La cadena anterior
# resuelve nombres segun el alcance estatico; hijos permite inspeccionar el arbol.


class SimboloDuplicadoError(Exception):
    # Indica que un nombre ya estaba declarado en el mismo ambiente. La entrada
    # existente se conserva para mostrar la posicion original en el diagnostico.
    def __init__(self, anterior):
        # Guarda la entrada que produjo el conflicto.
        self.anterior = anterior


class TablaSimbolos:
    # Ambiente con una tabla hash propia y un enlace al ambiente exterior.
    def __init__(self, nombre="global", anterior=None):
        # nombre es una ruta legible, por ejemplo global.demo. anterior apunta al
        # ambiente exterior o vale None para la raiz. Cada ambiente nuevo tambien
        # se registra en hijos para que el arbol pueda recorrerse hacia abajo.
        self.nombre = nombre
        self.tabla = {}
        self.anterior = anterior
        self.hijos = []
        if anterior is not None:
            anterior.hijos.append(self)

    @staticmethod
    def _normalizar(nombre):
        # Pascal no distingue mayusculas y minusculas en sus identificadores.
        return nombre.casefold()

    def insertar(
        self,
        nombre,
        tipo,
        categoria,
        columna,
        linea,
        parametros=None,
    ):
        # Solo se revisa la tabla local: se puede sombrear un nombre exterior,
        # pero no declararlo dos veces en el mismo ambiente. El resultado es el
        # diccionario mutable almacenado; luego puede completarse con el ambiente
        # de una rutina o con el estado del retorno de una funcion.
        clave = self._normalizar(nombre)
        if clave in self.tabla:
            raise SimboloDuplicadoError(self.tabla[clave])

        # Todos los simbolos comparten la misma estructura para simplificar la
        # presentacion de la tabla. Algunos campos solo tienen sentido para
        # rutinas o para la variable implicita de retorno de una funcion.
        simbolo = {
            "nombre": nombre,
            "tipo": tipo,
            "categoria": categoria,
            "ambito": self.nombre,
            "linea": linea,
            "columna": columna,
            "parametros": parametros or [],
            "nombre_original_funcion": None,
            "resultado_asignado": False,
            "ambito_local": None,
        }
        self.tabla[clave] = simbolo
        return simbolo

    def buscar_local(self, nombre):
        # Busca solo en este ambiente, con costo promedio O(1).
        return self.tabla.get(self._normalizar(nombre))

    def buscar(self, nombre):
        # Recorre los ambientes hacia afuera y devuelve la declaracion visible
        # mas cercana. Su costo es O(d), donde d es la profundidad de ambientes.
        ambiente = self
        while ambiente is not None:
            simbolo = ambiente.buscar_local(nombre)
            if simbolo is not None:
                return simbolo
            ambiente = ambiente.anterior
        return None

    def buscar_rutina(self, nombre):
        # Una variable local con el mismo nombre no detiene esta busqueda: se
        # continua hacia afuera hasta encontrar una funcion o procedimiento. Esto
        # permite hallar la firma de una funcion desde su propio ambiente, donde
        # el nombre local representa la variable implicita de retorno.
        ambiente = self
        while ambiente is not None:
            simbolo = ambiente.buscar_local(nombre)
            if simbolo is not None and simbolo["categoria"] in {"procedimiento", "funcion"}:
                return simbolo
            ambiente = ambiente.anterior
        return None
