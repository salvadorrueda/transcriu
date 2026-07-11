#!/usr/bin/env python3
"""echotext_l — Transcripció de veu a text en català.

Escolta el micròfon i transcriu cada frase amb el servei gratuït
Google Web Speech. Pensat per a ordinadors amb pocs recursos:
la feina pesada es fa al núvol.
"""

import argparse
import contextlib
import os
import subprocess
import sys

# Si no ens executem amb el Python del venv però el venv existeix al costat
# de l'script, ens re-executem amb ell: així './transcriu.py' funciona
# directament sense activar res.
_VENV_PYTHON = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            ".venv", "bin", "python")
if (os.path.exists(_VENV_PYTHON)
        and os.path.abspath(sys.executable) != os.path.abspath(_VENV_PYTHON)):
    os.execv(_VENV_PYTHON, [_VENV_PYTHON] + sys.argv)

try:
    import pyperclip
    import speech_recognition as sr
except ImportError:
    print("Falten les dependències. Crea l'entorn i instal·la-les amb:\n"
          "  python3 -m venv .venv\n"
          "  .venv/bin/pip install -r requirements.txt",
          file=sys.stderr)
    sys.exit(1)


@contextlib.contextmanager
def sense_soroll_alsa():
    """Amaga els avisos d'ALSA/JACK que PortAudio escriu a stderr en obrir l'àudio."""
    stderr_original = os.dup(2)
    try:
        with open(os.devnull, "w") as devnull:
            os.dup2(devnull.fileno(), 2)
        yield
    finally:
        os.dup2(stderr_original, 2)
        os.close(stderr_original)


def copia_al_porta_retalls(text):
    """Copia el text al porta-retalls sense que es perdi en sortir.

    A X11 la selecció la manté viu el procés que l'ha copiada. Llancem xclip
    en una sessió pròpia (setsid) perquè el Ctrl+C que atura l'script no el
    mati i el text segueixi disponible després de sortir. Si no hi ha xclip,
    es recorre a pyperclip com fins ara.
    """
    try:
        p = subprocess.Popen(["xclip", "-selection", "clipboard"],
                             stdin=subprocess.PIPE, close_fds=True,
                             start_new_session=True)
        p.communicate(input=text.encode("utf-8"))
    except FileNotFoundError:
        pyperclip.copy(text)


def llista_microfons():
    with sense_soroll_alsa():
        noms = sr.Microphone.list_microphone_names()
    if not noms:
        print("No s'ha trobat cap micròfon.")
        return
    print("Micròfons disponibles:")
    for index, nom in enumerate(noms):
        print(f"  [{index}] {nom}")


def transcriu(args):
    recognizer = sr.Recognizer()

    try:
        with sense_soroll_alsa():
            microfon = sr.Microphone(device_index=args.dispositiu)
    except OSError as e:
        print(f"Error obrint el micròfon: {e}", file=sys.stderr)
        print("Prova 'transcriu.py --mics' per veure els dispositius disponibles.",
              file=sys.stderr)
        sys.exit(1)

    with contextlib.ExitStack() as pila:
        with sense_soroll_alsa():
            font = pila.enter_context(microfon)
        print("Calibrant el soroll ambient... (1 segon de silenci)")
        recognizer.adjust_for_ambient_noise(font, duration=1)
        print(f"A punt. Parla en {args.llengua}. Atura amb Ctrl+C.")
        print("El text dictat es va copiant al porta-retalls (tota la sessió).")
        if args.output:
            print(f"El text s'afegirà a: {args.output}")

        frases = []
        porta_retalls_actiu = True
        while True:
            try:
                audio = recognizer.listen(font)
            except KeyboardInterrupt:
                raise

            try:
                text = recognizer.recognize_google(audio, language=args.llengua)
            except sr.UnknownValueError:
                print("(no s'ha entès, torna-ho a provar)")
                continue
            except sr.RequestError as e:
                print(f"(error de connexió amb el servei: {e})", file=sys.stderr)
                continue

            print(f"> {text}")
            frases.append(text)
            if porta_retalls_actiu:
                try:
                    copia_al_porta_retalls(" ".join(frases))
                except (OSError, pyperclip.PyperclipException) as e:
                    porta_retalls_actiu = False
                    print(f"(no es pot copiar al porta-retalls, es continua sense: {e})",
                          file=sys.stderr)
            if args.output:
                with open(args.output, "a", encoding="utf-8") as f:
                    f.write(text + "\n")


def main():
    parser = argparse.ArgumentParser(
        description="Transcripció de veu a text en català des del micròfon "
                    "(Google Web Speech, gratuït).")
    parser.add_argument("-o", "--output", metavar="FITXER",
                        help="fitxer on afegir el text transcrit (mode append)")
    parser.add_argument("-l", "--llengua", default="ca-ES",
                        help="codi de llengua (per defecte: ca-ES)")
    parser.add_argument("-d", "--dispositiu", type=int, metavar="N",
                        help="índex del micròfon a utilitzar (vegeu --mics)")
    parser.add_argument("--mics", action="store_true",
                        help="llista els micròfons disponibles i surt")
    args = parser.parse_args()

    if args.mics:
        llista_microfons()
        return

    try:
        transcriu(args)
    except KeyboardInterrupt:
        print("\nFins aviat!")


if __name__ == "__main__":
    main()
