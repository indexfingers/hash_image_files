def list_files(path):
    import glob
    import os
    print('finding all files under {}'.format(path))
    files =  [f for f in glob.glob(path + "**", recursive=True) if not os.path.isdir(f)]
    print('found {} files'.format(len(files)))
    
    return files



def is_valid_image(files):
    print('checking for valid image files')
    import imghdr
    valid = []
    types = []
    cnt=0
    for f in files:
        try:
            wt = imghdr.what(f)
            if wt is not None:
                valid.append(True)
                cnt = cnt+1
            else:
                valid.append(False)

            types.append(wt)
        except Exception as ex:
            valid.append(False)
            types.append(None)
    print('found {} valid image files'.format(cnt))
    return valid,types

    
    
def get_uuids(files,valid):
    print('hashing files to generate uuids')
    import ut_lite
    uuids = []
    for i,f in enumerate(files):
        if valid[i] is True:
            uuids.append(str(ut_lite.get_file_uuid(f)))
        else:
            uuids.append("None")
    return uuids


def grab_files(filename):
    print('getting files specified in {}'.format(filename))
    with open(filename) as f:
        lines = [line.rstrip() for line in f]
    print('got {} files'.format(len(lines)))
    return lines


def kill_invalid(in_lst,valid):
    out_lst = []
    for i,v in enumerate(valid):
        if v is True:
            out_lst.append(in_lst[i])
    return out_lst


def main(rt,dst,files_file):
    if files_file is not None:
        files = grab_files(files_file)
        valid = [True for f in files]
        types = ['Not checked' for f in files]
    else:   
        files = list_files(rt)
        valid,types = is_valid_image(files)
    uuids = get_uuids(files,valid)
    # kill anything that's not an image
    uuids = kill_invalid(uuids,valid)
    files = kill_invalid(files,valid)
    types = kill_invalid(types,valid)
    import csv
    with open(dst, 'w', newline='') as file:
        writer = csv.writer(file)
        for i,f in enumerate(files):
            try:
                writer.writerow([f, uuids[i], types[i]])
            except:
                print('failed to write {}'.format(f))
    print('uuids saved to {}'.format(dst))
            
            
import argparse
if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--rt')
    parser.add_argument('--dst')
    parser.add_argument('--file')
    args = parser.parse_args()
    print('got {}, {} and {}'.format(args.rt,args.file, args.dst))
    main(args.rt,args.dst,args.file)

