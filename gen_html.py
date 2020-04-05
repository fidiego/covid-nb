import logging
import os

from nbconvert import HTMLExporter


logger = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def main():
    logger.warning(f"Looking for notebooks in dir:{BASE_DIR}")
    notebooks = [f for f in os.listdir(BASE_DIR) if f.split(".")[-1] == "ipynb"]
    logger.info(f"Found {len(notebooks):02d} notebooks")
    for nb in notebooks:
        nb = os.path.join(BASE_DIR, nb)
        logger.warning(f" ‣ converting: {nb}")
        os.system(f"jupyter nbconvert --to html {nb}")
    lis = [
        f"""<li><a href="{nb.replace('ipynb', 'html')}">{nb}</a></li>"""
        for nb in notebooks
    ]
    index_html = f"<ul>{''.join(lis)}</ul>"
    with open(os.path.join(BASE_DIR, 'index.html'), 'w+') as openfile:
        openfile.write(index_html)



if __name__ == "__main__":
    main()
