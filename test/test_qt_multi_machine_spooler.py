import unittest

from test import bootstrap
from madgrav.device import basedevice
from madgrav.extra import cag

try:
    from PyQt6.QtWidgets import QApplication
    from madgrav.qt.qt_laser_dialogs import ProductionQueueDialog
    from madgrav.tools.production_queue import ProductionQueueManager, ProductionJob
    HAS_QT = True
except ImportError:
    HAS_QT = False


@unittest.skipUnless(HAS_QT, "PyQt6 not installed")
class TestQtMultiMachineSpooler(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_production_queue_multi_machine_management(self):
        mgr = ProductionQueueManager()
        job1 = mgr.add_job("Plaques Inox #1", target_machine_id="galvo_fiber_0", priority=1, estimated_sec=120)
        job2 = mgr.add_job("Decoupe Bois #2", target_machine_id="ruida_co2_0", priority=2, estimated_sec=300)

        self.assertEqual(len(mgr.jobs), 2)
        self.assertEqual(job1.target_machine_id, "galvo_fiber_0")
        self.assertEqual(job2.target_machine_id, "ruida_co2_0")

        fiber_jobs = mgr.get_jobs_for_machine("galvo_fiber_0")
        self.assertEqual(len(fiber_jobs), 1)
        self.assertEqual(fiber_jobs[0].name, "Plaques Inox #1")

        mgr.update_job_status(job1.job_id, "En cours")
        self.assertEqual(job1.status, "En cours")

    def test_production_queue_dialog_ui(self):
        mgr = ProductionQueueManager()
        mgr.add_job("Job A", target_machine_id="laser_1")
        mgr.add_job("Job B", target_machine_id="laser_2")

        dlg = ProductionQueueDialog(manager=mgr)
        self.assertIsNotNone(dlg.table_queue)
        self.assertIsNotNone(dlg.combo_machine_filter)

        self.assertGreaterEqual(dlg.table_queue.rowCount(), 2)

        # Filter by machine
        idx = dlg.combo_machine_filter.findData("laser_1")
        if idx >= 0:
            dlg.combo_machine_filter.setCurrentIndex(idx)
            self.assertEqual(dlg.table_queue.rowCount(), 1)
        dlg.close()


if __name__ == "__main__":
    unittest.main()
