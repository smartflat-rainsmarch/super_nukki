// UI2PSD Figma Plugin - Main Code
// This runs in the Figma sandbox (no DOM access)

figma.showUI(__html__, { width: 340, height: 320 });

figma.ui.onmessage = async (msg) => {
  if (msg.type === 'import') {
    try {
      await importFromUI2PSD(msg.shareCode, msg.apiUrl);
    } catch (err) {
      figma.ui.postMessage({ type: 'error', text: 'Import failed: ' + err.message });
    }
  }
};

async function importFromUI2PSD(shareCode, apiUrl) {
  figma.ui.postMessage({ type: 'status', text: 'Fetching layer data...' });

  // Fetch shared data from UI2PSD API
  const url = `${apiUrl}/api/share/${shareCode}`;
  const res = await fetch(url);

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Request failed' }));
    throw new Error(err.detail || `HTTP ${res.status}`);
  }

  const data = await res.json();
  const { canvas_size, layers } = data;

  figma.ui.postMessage({ type: 'status', text: `Creating frame (${canvas_size.width}x${canvas_size.height})...` });

  // Create main frame
  const frame = figma.createFrame();
  frame.name = 'UI2PSD Import';
  frame.resize(canvas_size.width, canvas_size.height);
  frame.fills = [{ type: 'SOLID', color: { r: 1, g: 1, b: 1 } }];

  // Group layers by type for naming
  const typeCounts = {};

  for (let i = 0; i < layers.length; i++) {
    const layer = layers[i];
    figma.ui.postMessage({ type: 'status', text: `Importing layer ${i + 1}/${layers.length}...` });

    const pos = layer.position;
    if (!pos) continue;

    // Track type counts for naming
    typeCounts[layer.type] = (typeCounts[layer.type] || 0) + 1;
    const layerName = layer.text_content || `${layer.type}_${typeCounts[layer.type]}`;

    if (layer.type === 'text' && layer.text_content) {
      // Create text node
      try {
        const textNode = figma.createText();
        await figma.loadFontAsync({ family: "Inter", style: "Regular" });
        textNode.characters = layer.text_content;
        textNode.x = pos.x;
        textNode.y = pos.y;
        textNode.resize(pos.w, pos.h);
        textNode.name = layerName;
        frame.appendChild(textNode);
      } catch (fontErr) {
        // Fallback: create rectangle with name
        const rect = figma.createRectangle();
        rect.x = pos.x;
        rect.y = pos.y;
        rect.resize(pos.w, pos.h);
        rect.name = layerName + ' (text fallback)';
        rect.fills = [{ type: 'SOLID', color: { r: 0.95, g: 0.95, b: 0.95 } }];
        frame.appendChild(rect);
      }
    } else if (layer.image_url) {
      // Create rectangle with image
      try {
        const imgUrl = `${apiUrl}${layer.image_url}`;
        const imgRes = await fetch(imgUrl);
        const imgBuffer = await imgRes.arrayBuffer();
        const imgData = new Uint8Array(imgBuffer);
        const image = figma.createImage(imgData);

        const rect = figma.createRectangle();
        rect.x = pos.x;
        rect.y = pos.y;
        rect.resize(pos.w, pos.h);
        rect.name = layerName;
        rect.fills = [{
          type: 'IMAGE',
          imageHash: image.hash,
          scaleMode: 'FILL',
        }];
        frame.appendChild(rect);
      } catch (imgErr) {
        // Fallback: empty rectangle
        const rect = figma.createRectangle();
        rect.x = pos.x;
        rect.y = pos.y;
        rect.resize(pos.w, pos.h);
        rect.name = layerName + ' (image failed)';
        rect.fills = [{ type: 'SOLID', color: { r: 0.9, g: 0.9, b: 0.9 } }];
        frame.appendChild(rect);
      }
    } else {
      // Generic rectangle
      const rect = figma.createRectangle();
      rect.x = pos.x;
      rect.y = pos.y;
      rect.resize(pos.w, pos.h);
      rect.name = layerName;
      rect.fills = [{ type: 'SOLID', color: { r: 0.95, g: 0.95, b: 0.95 } }];
      frame.appendChild(rect);
    }
  }

  // Center the frame in viewport
  figma.viewport.scrollAndZoomIntoView([frame]);

  figma.ui.postMessage({
    type: 'done',
    text: `Import complete! ${layers.length} layers created.`,
  });
}
