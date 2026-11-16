"""Flujo de recortes con imágenes sintéticas: sin credenciales ni avatar personal."""
import contextlib
import hashlib
import io
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from PIL import Image, ImageDraw

from avatar import config, gestos, rostro, componer


class GestosTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.character = self.root / 'personaje'
        self.poses = self.character / 'poses'
        self.poses.mkdir(parents=True)
        self.face = {'boca':{'x':529,'y':366,'ancho':110},
                     'ojos':{'izq':{'x':468,'y':266},'der':{'x':569,'y':257}},
                     'ojo':{'ancho':72,'alto':28},'vello_facial':False}
        self.master = Image.new('RGBA',(1024,1536),'#f8b183')
        ImageDraw.Draw(self.master).ellipse((480,350,575,390),fill='#b95068')
        self.master.save(self.poses/'neutral.png')
        self.manifest = {'version':2,'lienzo':{'ancho':1024,'alto':1536},
                         'poses':{'neutral':{'archivo':'poses/neutral.png',
                         'boca':{'x':529,'y':366,'escala':110/140},'ojos':self.face['ojos']}}}
        self.write(self.character/'cara.json',self.face)
        self.write(self.character/'manifest.json',self.manifest)
        self.write(self.root/'avatar.json',{'rostro':{'sistema':'svg'}})
        stack = contextlib.ExitStack()
        self.addCleanup(stack.close)
        stack.enter_context(patch.multiple(gestos,ROOT=self.root,PERSONAJE=self.character,POSES=self.poses,
            CARA=self.character/'cara.json',MANIFEST=self.character/'manifest.json',LAYERS=self.character/'layers'))
        stack.enter_context(patch.multiple(rostro,PERSONAJE=self.character,CONFIG={'rostro':{'sistema':'svg'}}))
        stack.enter_context(patch.object(config,'CARA',self.character/'cara.json'))
        stack.enter_context(patch.multiple(componer,MANIFEST=self.character/'manifest.json',POSES=self.poses,
            LAYERS=self.character/'layers',MOTION=self.root/'motion'))
        stack.enter_context(contextlib.redirect_stdout(io.StringIO()))
        stack.enter_context(contextlib.redirect_stderr(io.StringIO()))
        gestos.cmd_prompts(SimpleNamespace())
        for i,name in enumerate(gestos.GESTOS):
            image = self.master.copy()
            # Deliberate changes to body/background must never replace the original.
            ImageDraw.Draw(image).rectangle((0,900,1024,1536),fill=(i*25,0,0,255))
            image.save(gestos.carpeta()/'inbox'/f'{name}.png')

    def write(self,path,data):
        path.parent.mkdir(parents=True,exist_ok=True)
        path.write_text(json.dumps(data))

    def read(self,path):
        return json.loads(path.read_text())

    def activate(self):
        folder = gestos.preparar()
        gestos.cmd_activar(SimpleNamespace(aprobado=True))
        return folder

    def test_preparation_does_not_activate_and_versions_are_immutable(self):
        first = gestos.preparar()
        before = {p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in first.iterdir()}
        second = gestos.preparar()
        self.assertNotEqual(first,second)
        self.assertEqual(before,{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in first.iterdir()})
        self.assertNotIn('recortes',self.read(self.character/'manifest.json'))
        self.assertEqual(self.read(self.root/'avatar.json')['rostro']['sistema'],'svg')
        descriptor = self.read(first/'recortes.json')
        self.assertEqual(len(descriptor['bocas']),5)
        self.assertEqual(sum(len(states) for states in descriptor['ojos'].values()),4)
        self.assertTrue((first/'revision.png').exists())
        self.assertEqual((self.poses/'neutral.png').read_bytes(),self.master_bytes())

    def master_bytes(self):
        out = io.BytesIO()
        self.master.save(out,'PNG')
        return out.getvalue()

    def test_approval_required_and_both_switch_directions_preserve_pieces(self):
        folder = gestos.preparar()
        with self.assertRaises(SystemExit):
            gestos.cmd_activar(SimpleNamespace(aprobado=False))
        gestos.cmd_activar(SimpleNamespace(aprobado=True))
        pointer = self.read(self.character/'cara.json')['recortes']
        self.assertIn('recortes',self.read(self.character/'manifest.json'))
        gestos.cmd_usar(SimpleNamespace(sistema='svg'))
        self.assertNotIn('recortes',self.read(self.character/'manifest.json'))
        self.assertEqual(self.read(self.character/'cara.json')['recortes'],pointer)
        self.assertTrue((folder/'a.png').exists())
        gestos.cmd_usar(SimpleNamespace(sistema='recortes'))
        self.assertIn('recortes',self.read(self.character/'manifest.json'))

    def test_missing_piece_blocks_composition_without_svg_fallback(self):
        folder = self.activate()
        (folder/'a.png').unlink()
        with patch.object(rostro,'CONFIG',{'rostro':{'sistema':'recortes'}}):
            with self.assertRaises(SystemExit):
                componer.sync_avatar()
        self.assertFalse((self.root/'motion/assets/avatar').exists())
        self.assertEqual(self.read(self.root/'avatar.json')['rostro']['sistema'],'recortes')

    def test_sync_copies_selected_system_and_all_pieces(self):
        folder = self.activate()
        with patch.object(rostro,'CONFIG',{'rostro':{'sistema':'recortes'}}):
            componer.sync_avatar()
        dest = self.root/'motion/assets/avatar'
        self.assertIn('"recortes"',(dest/'manifest.js').read_text())
        self.assertTrue((dest/'layers'/folder.name/'a.png').exists())
        with patch.object(rostro,'CONFIG',{'rostro':{'sistema':'svg'}}):
            componer.sync_avatar()
        self.assertNotIn('"recortes"',(dest/'manifest.js').read_text())

    def test_changed_master_blocks_recortes(self):
        self.activate()
        Image.new('RGBA',self.master.size,'red').save(self.poses/'neutral.png')
        with self.assertRaises(SystemExit):
            gestos.cmd_usar(SimpleNamespace(sistema='recortes'))

    def test_stale_export_blocks_preparation(self):
        Image.new('RGBA',self.master.size,'red').save(self.poses/'neutral.png')
        with self.assertRaises(SystemExit):
            gestos.preparar()

    def test_new_master_archives_stale_inputs_before_export(self):
        before = (gestos.carpeta()/'inbox/a.png').read_bytes()
        Image.new('RGBA',self.master.size,'red').save(self.poses/'neutral.png')
        gestos.cmd_prompts(SimpleNamespace())
        self.assertEqual((gestos.carpeta()/'_anteriores/referencia-v1/inbox/a.png').read_bytes(),before)
        self.assertFalse((gestos.carpeta()/'inbox/a.png').exists())

    def test_failed_switch_does_not_change_files(self):
        paths = [self.character/'cara.json',self.character/'manifest.json',self.root/'avatar.json']
        before = [p.read_bytes() for p in paths]
        with self.assertRaises(SystemExit):
            gestos.cmd_usar(SimpleNamespace(sistema='recortes'))
        self.assertEqual(before,[p.read_bytes() for p in paths])

    def test_misaligned_canvas_rejected_without_resize(self):
        Image.new('RGB',(512,768),'white').save(gestos.carpeta()/'inbox/a.png')
        with self.assertRaises(SystemExit):
            gestos.preparar()
        self.assertFalse((self.character/'layers').exists())

    def test_invalid_box_rejected(self):
        settings = self.read(gestos.carpeta()/'ajustes.json')
        settings['boca'] = [-10,338,120,80]
        self.write(gestos.carpeta()/'ajustes.json',settings)
        with self.assertRaises(SystemExit):
            gestos.preparar()

    def test_missing_legacy_choice_and_explicit_svg(self):
        self.assertNotIn('recortes',rostro.aplicar(self.manifest,self.face,{}))
        self.activate()
        face = self.read(self.character/'cara.json')
        self.assertIn('recortes',rostro.aplicar(self.manifest,face,{}))
        self.assertNotIn('recortes',rostro.aplicar(self.manifest,face,{'rostro':{'sistema':'svg'}}))

    def test_unsafe_path_and_invalid_descriptor_rejected(self):
        folder = self.activate()
        descriptor = self.read(folder/'recortes.json')
        descriptor['bocas']['A']['archivo'] = '../outside.png'
        with self.assertRaises(ValueError):
            rostro.validar(descriptor)
        descriptor = self.read(folder/'recortes.json')
        descriptor['referencia']['boca']['escala'] = 0
        with self.assertRaises(ValueError):
            rostro.validar(descriptor)
        descriptor = self.read(folder/'recortes.json')
        descriptor['bocas']['A']['ancho'] += 1
        with self.assertRaises(ValueError):
            rostro.validar(descriptor)


if __name__ == '__main__':
    unittest.main()
