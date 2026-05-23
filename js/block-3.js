
    function mobileNavTo(section) {
        document.querySelectorAll('.mobile-nav-item').forEach(i => i.classList.remove('active'));
        event.currentTarget.classList.add('active');
        switch(section) {
            case 'home': window.scrollTo({top:0,behavior:'smooth'}); break;
            case 'modules': document.getElementById('section-modules')?.scrollIntoView({behavior:'smooth'}); break;
            case 'coord': openV3Panel(); break;
            case 'monitor': openMonitorPanel(); break;
            case 'docs': window.open('http://127.0.0.1:8765/docs','_blank'); break;
        }
    }
    // Detect mobile
    if (/Android|iPhone|iPad|iPod|Mobile/i.test(navigator.userAgent)) {
        document.body.classList.add('mobile-device');
    }
    