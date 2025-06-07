import sys

def main():
    from src.pys4_avatar_maker.ui_main import main as gui_main
    gui_main()

if __name__ == "__main__":
    if '--compile' in sys.argv:
        from src.pys4_avatar_maker.compile_dist import build_exe
        build_exe()
        sys.exit(0)
    main() 