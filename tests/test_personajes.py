import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from avatar import config, personajes, prompts


class PersonajesTests(unittest.TestCase):
    def test_legacy_and_separate_character_directories(self):
        base = Path('/tmp/personajes')
        self.assertEqual(config.carpeta_personaje(None, base), base)
        self.assertNotEqual(config.carpeta_personaje('presentador', base),
                            config.carpeta_personaje('otro', base))
        for invalid in ('', '../otro', '/tmp/otro', 'uno/dos', 3):
            with self.assertRaises(ValueError):
                config.carpeta_personaje(invalid, base)

    def test_selection_preserves_configuration_and_rejects_missing_character(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            base = root / 'personaje'
            folder = base / 'otro'
            folder.mkdir(parents=True)
            (folder / 'personaje.json').write_text('{}')
            cfg = {'personaje_activo': 'presentador', 'rostro': {'sistema': 'svg'}}
            with patch.multiple(personajes, ROOT=root, CONFIG=cfg), \
                 patch.object(personajes, 'carpeta_personaje',
                              side_effect=lambda name: config.carpeta_personaje(name, base)):
                personajes.cmd_usar(SimpleNamespace(nombre='otro'))
                saved = json.loads((root / 'avatar.json').read_text())
                self.assertEqual(saved, {**cfg, 'personaje_activo': 'otro'})
                with self.assertRaises(SystemExit):
                    personajes.cmd_usar(SimpleNamespace(nombre='ausente'))
                self.assertEqual(json.loads((root / 'avatar.json').read_text()), saved)

    def test_image_destinations_follow_selected_character(self):
        base = config.ROOT / 'personaje' / 'otro'
        with patch.multiple(prompts, HOJA=base / 'hoja-de-personaje.png', INBOX=base / 'inbox'):
            self.assertEqual(prompts.destino('00'), 'personaje/otro/hoja-de-personaje.png')
            self.assertEqual(prompts.destino('01'), 'personaje/otro/inbox/01-neutral.png')
            self.assertIn('personaje/otro/hoja-de-personaje.png', prompts.adjuntos('01'))


if __name__ == '__main__':
    unittest.main()
