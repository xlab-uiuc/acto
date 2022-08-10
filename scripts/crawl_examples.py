import argparse
import glob, os
import yaml

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Crawl CR examples in the project repo')

    parser.add_argument('--dir', dest='dir', help='Project repo dir', required=True)
    parser.add_argument('--kind', '-k', dest='kind', help='CR kind', required=True)
    # parser.add_argument('--dest',
    #                     dest='dest',
    #                     help='Directory to store the crawlled examples',
    #                     required=True)

    args = parser.parse_args()

    results = []

    for file in glob.glob(os.path.join(args.dir, '**', '*.yaml'), recursive=True):
        with open(file, 'r') as yaml_file:
            try:
                file_content = yaml.load(yaml_file, Loader=yaml.FullLoader)
            except:
                continue
            if 'kind' in file_content and file_content['kind'] == args.kind:
                print(file)
                results.append(file_content)

    with open('examples.yaml', 'w') as out_file:
        yaml.dump_all(results, out_file)

