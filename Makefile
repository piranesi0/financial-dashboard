DB      := financials.sqlite
PIDFILE := .server.pid
LOGFILE := .server.log
CMD     := .venv/bin/financials web $(DB)

.venv/bin/financials: pyproject.toml
	uv pip install -e .

.PHONY: run start stop logs install

install: .venv/bin/financials

run: .venv/bin/financials
	$(CMD)

start: .venv/bin/financials
	@if [ -f $(PIDFILE) ] && kill -0 $$(cat $(PIDFILE)) 2>/dev/null; then \
		echo "Already running (pid $$(cat $(PIDFILE)))"; \
	else \
		$(CMD) >> $(LOGFILE) 2>&1 & echo $$! > $(PIDFILE); \
		echo "Started (pid $$(cat $(PIDFILE))) — logs: $(LOGFILE)"; \
	fi

stop:
	@if [ -f $(PIDFILE) ]; then \
		kill $$(cat $(PIDFILE)) && rm $(PIDFILE) && echo "Stopped."; \
	else \
		echo "Not running."; \
	fi

logs:
	tail -f $(LOGFILE)
