'''
Python code to convert a .dat file to a readable .dat file
'''
import numpy as np


def read_file(fname):
    '''Read a corrupted .dat file and return the data'''
    lines = []
    with open(fname, 'r') as f:
        for k,line in enumerate(f.readlines()):
            if k in [0, 2, 3, 4, 5]:
                lines.append(line)
            elif k == 1:
                spacing = np.round(float(line.strip()), 4)
                lines.append('{:10.4f}\n'.format(spacing))
            else:
                try:
                    a,b,n,d = line.strip().split()

                    a = float(a)
                    b = spacing * np.round(float(b) / spacing, 0)
                    c = int(np.round(float(n),0))

                    lines.append(
                        f'{a:>8.4f}    {b:>7.4f}    {c:d}    {d}\n'
                    )
                except ValueError as e:
                    if k < 10:
                        print(e)
                        raise ValueError
                    else:
                        lines.append(line)
    
    return lines

def write_file(lines, outname=None, fname=None):
    '''Write ERT data to a .dat file'''
    if (outname is None) and (fname is None):
        raise ValueError('Please provide a filename')
    
    if outname is None:
        outname = fname.split('.')[0] + '_corrected.' + fname.split('.')[1]
    
    with open(outname, 'w') as f:
        for line in lines:
            f.write(line)


if __name__=='__main__':
    import sys
    if len(sys.argv)>1:
        filename = sys.argv[1]
    else:
        print('You need to pass the filename')
    lines = read_file(filename)
    write_file(lines, fname=filename)

