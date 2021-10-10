from waldur_core.core import WaldurExtension

## Class to define Slurm static methods from waldur extension
class SlurmExtension(WaldurExtension):
    @staticmethod
    def django_app():
        return 'waldur_slurm'

    @staticmethod
    def rest_urls():
        from .urls import register_in

        return register_in

    @staticmethod
    def get_cleanup_executor():
        from waldur_slurm.executors import SlurmCleanupExecutor

        return SlurmCleanupExecutor
