import argparse
from pathlib import Path
from .detect import detect
from .core import save_environment, restore_environment

def main():
    parser=argparse.ArgumentParser(prog="linux-env")
    sub=parser.add_subparsers(dest="command",required=True)
    sub.add_parser("detect")
    save=sub.add_parser("save"); save.add_argument("destination",type=Path)
    restore=sub.add_parser("restore"); restore.add_argument("source",type=Path); restore.add_argument("--dry-run",action="store_true")
    args=parser.parse_args()
    if args.command=="detect":
        for k,v in detect().items(): print(f"{k}: {v}")
    elif args.command=="save":
        save_environment(args.destination); print(f"Environment saved to {args.destination}")
    elif args.command=="restore":
        for cmd in restore_environment(args.source,args.dry_run): print("$"," ".join(cmd))
if __name__=="__main__": main()
