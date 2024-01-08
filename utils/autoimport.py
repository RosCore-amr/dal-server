import os

class AutoImport:
    @staticmethod
    def importModule(module: str):
        exec(f"from {module} import *")

    @staticmethod
    def addFile(file_path: str):
        """
        Import file if path exists
        """
        if os.path.isfile(file_path):
            module = file_path.replace("/",".").replace("\\",".").replace(".py", "")
            AutoImport.importModule(module)

    @staticmethod
    def importAllFiles(root_dir: str, name: str = ""):
        """
        Import all files [by name] in a folder
        """
        folders = [root_dir]
        for fd in folders:
            for it in os.scandir(fd):
                if it.is_dir():
                    # If is folder, and not __pycache
                    if "__pycache__" in it.path:
                        continue
                    
                    folders.append(it.path)
                elif name == "" or\
                        it.name == name:
                    # If name not defined
                    # or if is needed file
                    AutoImport.addFile(it.path)
