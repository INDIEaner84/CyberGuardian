// Minimal PNG decoder for Chrome screenshots (8-bit RGB/RGBA, non-interlaced).
import zlib from 'node:zlib';

const SIGNATURE = Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]);

function paeth(left, up, upLeft) {
  const estimate = left + up - upLeft;
  const toLeft = Math.abs(estimate - left);
  const toUp = Math.abs(estimate - up);
  const toUpLeft = Math.abs(estimate - upLeft);
  if (toLeft <= toUp && toLeft <= toUpLeft) return left;
  return toUp <= toUpLeft ? up : upLeft;
}

/** @returns {{width: number, height: number, data: Uint8Array}} RGBA pixels */
export function decodePng(buffer) {
  if (!buffer.subarray(0, 8).equals(SIGNATURE)) throw new Error('not a PNG');
  let offset = 8;
  let width = 0; let height = 0; let colourType = 0; let bitDepth = 0; let interlace = 0;
  const chunks = [];
  while (offset < buffer.length) {
    const length = buffer.readUInt32BE(offset);
    const type = buffer.toString('ascii', offset + 4, offset + 8);
    const body = buffer.subarray(offset + 8, offset + 8 + length);
    if (type === 'IHDR') {
      width = body.readUInt32BE(0); height = body.readUInt32BE(4);
      bitDepth = body[8]; colourType = body[9]; interlace = body[12];
    } else if (type === 'IDAT') {
      chunks.push(body);
    } else if (type === 'IEND') {
      break;
    }
    offset += 12 + length;
  }
  if (bitDepth !== 8 || interlace !== 0 || ![2, 6].includes(colourType)) {
    throw new Error(`unsupported PNG (depth ${bitDepth}, colour type ${colourType}, interlace ${interlace})`);
  }
  const channels = colourType === 6 ? 4 : 3;
  const stride = width * channels;
  const raw = zlib.inflateSync(Buffer.concat(chunks));
  const pixels = new Uint8Array(width * height * channels);
  for (let row = 0; row < height; row += 1) {
    const filter = raw[row * (stride + 1)];
    const source = row * (stride + 1) + 1;
    const target = row * stride;
    for (let column = 0; column < stride; column += 1) {
      const value = raw[source + column];
      const left = column >= channels ? pixels[target + column - channels] : 0;
      const up = row > 0 ? pixels[target + column - stride] : 0;
      const upLeft = row > 0 && column >= channels ? pixels[target + column - stride - channels] : 0;
      let decoded;
      switch (filter) {
        case 0: decoded = value; break;
        case 1: decoded = value + left; break;
        case 2: decoded = value + up; break;
        case 3: decoded = value + ((left + up) >> 1); break;
        case 4: decoded = value + paeth(left, up, upLeft); break;
        default: throw new Error(`bad PNG filter ${filter}`);
      }
      pixels[target + column] = decoded & 0xff;
    }
  }
  if (channels === 4) return { width, height, data: pixels };
  const rgba = new Uint8Array(width * height * 4);
  for (let index = 0, out = 0; index < pixels.length; index += 3, out += 4) {
    rgba[out] = pixels[index]; rgba[out + 1] = pixels[index + 1]; rgba[out + 2] = pixels[index + 2]; rgba[out + 3] = 255;
  }
  return { width, height, data: rgba };
}
