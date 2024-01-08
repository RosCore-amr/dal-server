import pandas as pd
from io import BytesIO

class ImportExportExcel:
    @staticmethod
    def export_excel(data: dict) -> BytesIO:
        """
        Return excel buffer from dict
        """
        df = pd.DataFrame(data)

        excel_buffer = BytesIO()

        df.to_excel(excel_buffer, index=False)

        excel_buffer.seek(0)

        return excel_buffer