.PHONY: run deb lint screenshots clean

run:
	python3 htop_widget.py

deb:
	./scripts/build-deb.sh

lint: deb
	lintian --no-tag-display-limit dist/*.deb || true
	desktop-file-validate packaging/usr/share/applications/desktop-htop.desktop \
		packaging/etc/xdg/autostart/desktop-htop.desktop

screenshots:
	python3 scripts/screenshots.py

clean:
	rm -rf build __pycache__   # dist/ berisi .deb yang ikut di-commit, jangan dihapus
