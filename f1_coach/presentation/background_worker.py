"""BackgroundWorker — bir fonksiyonu arka plan thread'inde çalıştırıp
sonucunu ana (UI) thread'ine sinyal olarak geri döndüren küçük yardımcı.

Qt'de widget güncellemeleri yalnızca ana thread'de güvenlidir. Bu sınıf
yalnızca ARKA PLANDA çalışan fonksiyonu sarmalar — o fonksiyon hiçbir
widget'a dokunmamalı, yalnızca veri okuma/işleme yapmalı. Sonuç,
`finished` sinyaliyle ana thread'e teslim edilir; UI güncellemesi yalnızca
o sinyalin handler'ında yapılmalı (Qt'nin cross-thread sinyalleri otomatik
olarak alıcının thread'inde kuyruğa alınır, bu yüzden bu güvenlidir).
"""

from PyQt6.QtCore import QObject, QThread, pyqtSignal


class _WorkerObject(QObject):
    finished = pyqtSignal(object)
    failed = pyqtSignal(Exception)

    def __init__(self, fn, *args, **kwargs) -> None:
        super().__init__()
        self._fn = fn
        self._args = args
        self._kwargs = kwargs

    def run(self) -> None:
        try:
            result = self._fn(*self._args, **self._kwargs)
        except Exception as exc:
            self.failed.emit(exc)
        else:
            self.finished.emit(result)


class BackgroundWorker:
    """Bir fonksiyonu arka plan thread'inde çalıştırır.

    Kullanım:
        self._worker = BackgroundWorker(some_blocking_fn, arg1, arg2)
        self._worker.finished.connect(self._on_done)
        self._worker.failed.connect(self._on_error)
        self._worker.start()

    ÖNEMLİ: BackgroundWorker nesnesinin referansını (self._worker gibi)
    çağıran tarafta CANLI TUTMAK gerekir — Python GC'si thread bitmeden
    nesneyi toplarsa iş parçacığı beklenmedik şekilde sonlanabilir.
    """

    def __init__(self, fn, *args, **kwargs) -> None:
        self._thread = QThread()
        self._worker = _WorkerObject(fn, *args, **kwargs)
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.finished.connect(self._thread.quit)
        self._worker.failed.connect(self._thread.quit)

    @property
    def finished(self):
        return self._worker.finished

    @property
    def failed(self):
        return self._worker.failed

    def start(self) -> None:
        self._thread.start()