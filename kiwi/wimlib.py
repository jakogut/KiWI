from subprocess import Popen, PIPE

WIMLIB_IMAGEX_PATH = '/usr/bin/wimlib-imagex'

def wiminfo(wim_path):
    images = []

    index = 1
    while True:
        cmd = [WIMLIB_IMAGEX_PATH, 'info', wim_path, str(index)]
        p = Popen(cmd, stdout=PIPE, stderr=PIPE)
        output, err = p.communicate()
        if p.returncode != 0: break

        properties = {}
        image_info = output.decode('UTF-8').split('\n')
        for line in image_info:
            if ':' not in line: continue
            property, value = [token.strip() for token in line.split(':', maxsplit=1)]
            properties[property] = value

        images.append(properties)
        index += 1

    return images

if __name__ == '__main__':
    print(wiminfo('/mnt/nfs/home/nfs/win7_x64_sp1.wim'))
