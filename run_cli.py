import argparse
from src.pdfdirectory import add_directory

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Add content to PDF.')
    parser.add_argument('pdfPath', type=str, help='path of PDF')
    parser.add_argument('tocPath', type=str, help='path of contents file')
    parser.add_argument('--offset', type=int, default=0,
                        help='Page offset of contents')
    parser.add_argument('--l0', type=str,
                        default=r'^\d+\.\s?',
                        help='Regular expression of level 0 of content')
    parser.add_argument('--l1', type=str,
                        default=r'^\d+\.\d+\w?\s?',
                        help='Regular expression of level 1 of content')
    parser.add_argument('--l2', type=str,
                        default=r'^\d+\.\d+\.\d+\w?\s?',
                        help='Regular expression of level 2 of content')
    parser.add_argument('--l3', type=str,
                        default=r'^\d+\.\d+\.\d+\.\d+\w?\s?',
                        help='Regular expression of level 3 of content')
    parser.add_argument('--l4', type=str,
                        default=r'^\d+\.\d+\.\d+\.\d+\.\d+\w?\s?',
                        help='Regular expression of level 4 of content')
    parser.add_argument('--l5', type=str,
                        default=r'^\d+\.\d+\.\d+\.\d+\.\d+\.\d+\w?\s?',
                        help='Regular expression of level 5 of content')
    args = parser.parse_args()

    pdfPath = args.pdfPath
    tocPath = args.tocPath
    offset = args.offset

    # -- load toc
    f = open(tocPath)
    toc = f.read()
    f.close()
    add_directory(toc, offset, pdfPath,
                  args.l0, args.l1, args.l2, args.l3, args.l4, args.l5)
