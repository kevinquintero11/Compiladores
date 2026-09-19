#!/usr/bin/env python3
"""Ejecuta el analizador semantico sobre todos los archivos Pascal de la bateria."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


DIRECTORIO_SCRIPT = Path(__file__).resolve().parent
DIRECTORIO_PROYECTO = DIRECTORIO_SCRIPT.parent
sys.path.insert(0, str(DIRECTORIO_PROYECTO))

from analizadorSintactico import (  # noqa: E402
    EntradaNoValidaParaSintactico,
    analizar_archivo,
    generar_reporte,
)


def buscar_archivos_pascal(directorio: Path) -> list[Path]:
    return sorted(
        (
            ruta
            for ruta in directorio.iterdir()
            if ruta.is_file() and ruta.suffix.casefold() == ".pas"
        ),
        key=lambda ruta: ruta.name.casefold(),
    )


def evaluar_bateria(directorio_entrada: Path, directorio_salida: Path) -> int:
    if not directorio_entrada.is_dir():
        print(f"Error: no existe el directorio de entrada: {directorio_entrada}")
        return 1

    archivos = buscar_archivos_pascal(directorio_entrada)
    if not archivos:
        print(f"Error: no se encontraron archivos .pas en: {directorio_entrada}")
        return 1

    directorio_salida.mkdir(parents=True, exist_ok=True)
    correctos = 0
    con_errores = 0
    fallidos = 0

    for archivo in archivos:
        salida = directorio_salida / f"{archivo.stem}_salida.txt"
        try:
            resultado = analizar_archivo(archivo)
            salida.write_text(generar_reporte(resultado), encoding="utf-8")
            if resultado.ok:
                correctos += 1
                estado = "correcto"
            else:
                con_errores += 1
                estado = resultado.mensaje
        except (EntradaNoValidaParaSintactico, OSError, UnicodeError) as exc:
            fallidos += 1
            estado = f"no se pudo analizar: {exc}"
            try:
                salida.write_text(
                    f"Archivo analizado: {archivo.name}\nResultado: {estado}\n",
                    encoding="utf-8",
                )
            except OSError:
                pass

        print(f"{archivo.name}: {estado} -> {salida.name}")

    print(
        f"\nProcesados: {len(archivos)} | "
        f"Correctos: {correctos} | Con errores: {con_errores} | Fallidos: {fallidos}"
    )
    print(f"Reportes: {directorio_salida}")
    return 1 if fallidos else 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Evalua todos los archivos .pas con el analizador semantico."
    )
    parser.add_argument(
        "entrada",
        nargs="?",
        type=Path,
        default=DIRECTORIO_SCRIPT / "Semanticos",
        help="directorio con archivos .pas (por defecto: BatSemanticos/Semanticos)",
    )
    parser.add_argument(
        "-o",
        "--salida",
        type=Path,
        default=DIRECTORIO_SCRIPT / "Salidas",
        help="directorio para los reportes (por defecto: BatSemanticos/Salidas)",
    )
    argumentos = parser.parse_args()
    return evaluar_bateria(argumentos.entrada.resolve(), argumentos.salida.resolve())


if __name__ == "__main__":
    raise SystemExit(main())
