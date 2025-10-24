(function() {
    'use strict';

    function queryByClassPrefix(prefix) {
        return Array.from(document.querySelectorAll('div'))
            .find(el => Array.from(el.classList).some(c => c.startsWith(prefix)));
    }

    function addMenuItem() {
        const menuGroup = queryByClassPrefix('menu-bar_file-group');
        if (!menuGroup) return false;
        if (queryByClassPrefix('custom-test-item')) return true;

        const newItem = document.createElement('div');
        newItem.className = 'custom-test-item';
        newItem.classList.add(...Array.from(menuGroup.querySelectorAll('div'))
            .map(el => Array.from(el.classList)
            .filter(c => c.startsWith('menu-bar_menu-bar-item') || c.startsWith('menu-bar_hoverable')))
            .flat()
        );

        newItem.textContent = '🌱   BlockVine (Git)';

        newItem.addEventListener('click', () => {
            fetch('http://localhost:8617', { method: 'GET' })
            .then(response => {
                if (!response.ok) {
                    alert('Failed to connect to the BlockVine local backend. Please re-open  BlockVine and try again.');
                    return;
                }

                if (document.querySelector('#blockvine-sidebar')) return;

                const sidebar = document.createElement('div');
                sidebar.id = 'blockvine-sidebar';
                Object.assign(sidebar.style, {
                    position: 'fixed',
                    top: '0',
                    left: '0',
                    width: '360px',
                    height: '100%',
                    background: '#1e1e1e',
                    borderRight: '2px solid #444',
                    boxShadow: '4px 0 24px rgba(0,0,0,0.5)',
                              zIndex: 9999,
                              display: 'flex',
                              flexDirection: 'column',
                              transition: 'transform 0.25s ease, left 0.25s ease, right 0.25s ease',
                });

                const titleBar = document.createElement('div');
                Object.assign(titleBar.style, {
                    background: '#333',
                    color: '#fff',
                    padding: '12px 12px',
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    fontWeight: 'normal'
                });
                titleBar.textContent = '🌱 Git';

                const closeBtn = document.createElement('button');
                closeBtn.textContent = '×';
                Object.assign(closeBtn.style, {
                    background: '#222',
                    border: 'none',
                    borderRadius: '1em',
                    color: '#fff',
                    fontSize: '20px',
                    cursor: 'pointer',
                    fontWeight: 'bold'
                });
                closeBtn.onclick = () => sidebar.remove();

                const dockBtn = document.createElement('button');
                dockBtn.textContent = '⇄';
                Object.assign(dockBtn.style, {
                    background: '#222',
                    border: 'none',
                    borderRadius: '1em',
                    color: '#fff',
                    fontSize: '16px',
                    cursor: 'pointer',
                    fontWeight: 'bold',
                    marginRight: '8px'
                });

                let dockedLeft = true; // default position
                dockBtn.onclick = () => {
                    if (dockedLeft) {
                        sidebar.style.left = 'auto';
                        sidebar.style.right = '0';
                        sidebar.style.borderRight = 'none';
                        sidebar.style.borderLeft = '2px solid #444';
                    } else {
                        sidebar.style.right = 'auto';
                        sidebar.style.left = '0';
                        sidebar.style.borderLeft = 'none';
                        sidebar.style.borderRight = '2px solid #444';
                    }
                    dockedLeft = !dockedLeft;
                };

                const buttonContainer = document.createElement('div');
                buttonContainer.style.display = 'flex';
                buttonContainer.appendChild(dockBtn);
                buttonContainer.appendChild(closeBtn);

                titleBar.appendChild(buttonContainer);
                sidebar.appendChild(titleBar);

                const iframe = document.createElement('iframe');
                iframe.src = 'http://localhost:8617/gui';
                Object.assign(iframe.style, {
                    flex: '1',
                    border: 'none',
                    width: '100%',
                });
                sidebar.appendChild(iframe);

                document.body.appendChild(sidebar);
            })
            .catch(() => {
                alert('TurboWarp was not launched alongside BlockVine. Please open BlockVine from your app menu.');
            });
        });

        menuGroup.appendChild(newItem);
        return true;
    }

    const observer = new MutationObserver(() => {
        if (addMenuItem()) observer.disconnect();
    });
    observer.observe(document.body, { childList: true, subtree: true });

    addMenuItem();
})();
