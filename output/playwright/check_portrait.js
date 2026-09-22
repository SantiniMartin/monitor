async (page) => {
  const root = 'C:/Users/Marti/Desktop/monitorDjango/monitor';
  await page.route('**/*', route => {
    const pathname = route.request().url().replace(/^https?:\/\/[^/]+/, '').split('?')[0];
    if (pathname === '/camera') return route.fulfill({path: root+'/output/playwright/omr-portrait.html',contentType:'text/html'});
    if (pathname.startsWith('/static/evaluaciones_educativas/')) return route.fulfill({path:root+'/monitoreo/apps/evaluaciones_educativas/static/'+pathname.slice(8)});
    return route.fulfill({body:''});
  });
  const reports = [];
  for (const [screenWidth,screenHeight,width,height] of [[390,844,1600,900],[412,915,1200,1600],[375,812,900,1600],[1280,900,1600,900]]) {
    await page.setViewportSize({width:screenWidth,height:screenHeight});
    await page.goto('https://omr.test/camera');
    await page.evaluate(({width,height})=>{
      const source=document.createElement('canvas'); source.width=width; source.height=height;
      const ctx=source.getContext('2d');
      // Coordenadas codificadas como colores para comparar el recorte del JPEG.
      const data=ctx.createImageData(width,height);
      for(let y=0;y<height;y++) for(let x=0;x<width;x++) {
        const i=(y*width+x)*4;
        data.data[i]=Math.round(255*x/width); data.data[i+1]=Math.round(255*y/height); data.data[i+2]=100; data.data[i+3]=255;
      }
      ctx.putImageData(data,0,0);
      window.source=source;
      navigator.mediaDevices.getUserMedia=async()=>{
        const stream=source.captureStream(30);
        window.frameTimer=setInterval(()=>ctx.putImageData(data,0,0),100);
        return stream;
      };
      procesarImagen=async file=>{
        const image=await createImageBitmap(file);
        const preview=document.getElementById('canvas-preview'); preview.width=image.width; preview.height=image.height;
        const pctx=preview.getContext('2d');pctx.drawImage(image,0,0); image.close();
        window.result={width:preview.width,height:preview.height,samples:[[0.1,0.1],[0.5,0.5],[0.9,0.9]].map(([x,y])=>Array.from(pctx.getImageData(Math.floor(x*preview.width),Math.floor(y*preview.height),1,1).data))};
        clearInterval(window.frameTimer);
        preview.style.display='block'; document.getElementById('placeholder').style.display='none'; marcarZonaConImagen(true);
      };
    },{width,height});
    await page.locator('#btn-abrir-camara').click();
    await page.waitForFunction(()=>document.getElementById('video-live').readyState>=2);
    const before=await page.locator('#video-live').boundingBox();
    if(Math.abs(before.width/before.height-0.75)>0.001) throw new Error('Visor no vertical');
    await page.locator('#btn-capturar-live').click();
    await page.waitForFunction(()=>window.result);
    const result=await page.evaluate(()=>window.result);
    const after=await page.locator('#canvas-preview').boundingBox();
    if(Math.abs(after.width-before.width)>1||Math.abs(after.height-before.height)>1) throw new Error('Salto de encuadre al capturar');
    const cropW=Math.min(width,height*0.75), cropH=Math.min(height,width/0.75);
    for(let i=0;i<3;i++) {
      const p=[0.1,0.5,0.9][i];
      const expected=[255*((width-cropW)/2+p*cropW)/width,255*((height-cropH)/2+p*cropH)/height];
      if(Math.abs(result.samples[i][0]-expected[0])>5||Math.abs(result.samples[i][1]-expected[1])>5) throw new Error('JPEG distinto al encuadre visible');
    }
    reports.push({viewport:[screenWidth,screenHeight],source:[width,height],visor:[before.width,before.height],capture:[result.width,result.height]});
    if(screenWidth===390) await page.locator('#camera-zone').screenshot({path:'output/playwright/visor-vertical.png'});
  }
  await page.evaluate(reports=>window.qaReports=reports,reports);
}
