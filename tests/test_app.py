import ctypes
import subprocess
import sys
import tkinter as tk
import unittest
import uuid
from pathlib import Path
from unittest.mock import patch

import main


class AppTests(unittest.TestCase):
    def test_layout_at_common_scales(self):
        main.enable_dpi_awareness()
        for scale in (1, 1.25, 1.5, 2):
            with self.subTest(scale=scale):
                root = tk.Tk()
                root.withdraw()
                self.addCleanup(root.destroy)
                root.tk.call('tk', 'scaling', 96 * scale / 72)
                with patch.object(main.SimulatedInputApp, 'initialize_background_features'), patch.object(
                    main.SimulatedInputApp, 'load_config', return_value=main.DEFAULT_CONFIG.copy()
                ):
                    app = main.SimulatedInputApp(root)
                    root.deiconify()
                    root.update()
                    pending = [root]
                    while pending:
                        parent = pending.pop()
                        for child in parent.winfo_children():
                            pending.append(child)
                            if child.winfo_ismapped():
                                self.assertLessEqual(child.winfo_x() + child.winfo_width(), parent.winfo_width() + 2)
                                self.assertLessEqual(child.winfo_y() + child.winfo_height(), parent.winfo_height() + 2)
                                if child.winfo_class() in ('Label', 'TLabel', 'TButton'):
                                    self.assertGreaterEqual(child.winfo_width(), child.winfo_reqwidth() - 2)
                    app.use_random_var.set(False)
                    app.on_random_toggle()
                    self.assertTrue(app.min_speed_entry.instate(['disabled']))
                    self.assertTrue(app.fixed_speed_entry.instate(['!disabled']))
                root.withdraw()

    @unittest.skipUnless(sys.platform == 'win32', 'Windows mutex')
    def test_single_instance_across_processes(self):
        name = 'Local\\SimulatedInputTool.Test.' + uuid.uuid4().hex
        with patch.object(main, 'INSTANCE_MUTEX_NAME', name):
            handle = main.acquire_instance()
            self.assertIsNotNone(handle)
            try:
                code = (
                    'import main; '
                    f'main.INSTANCE_MUTEX_NAME = {name!r}; '
                    'assert main.acquire_instance() is None'
                )
                subprocess.run([sys.executable, '-c', code], cwd=Path(__file__).resolve().parents[1], check=True, timeout=10)
            finally:
                ctypes.windll.kernel32.CloseHandle(ctypes.c_void_p(handle))
            handle = main.acquire_instance()
            self.assertIsNotNone(handle)
            ctypes.windll.kernel32.CloseHandle(ctypes.c_void_p(handle))


if __name__ == '__main__':
    unittest.main()
