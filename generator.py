import argparse

from staticfg import CFGBuilder

if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument("pythonfile", help="The python file to be analyzed")
    args = parser.parse_args()
    
    cfg = CFGBuilder().build_from_file(args.pythonfile, args.pythonfile)
    cfg.build_visual('res', 'png')
