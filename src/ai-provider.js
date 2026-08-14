export class AIImageProvider {
  constructor() {
    this.available = false;
    this.name = 'Nenhum provider configurado';
  }

  async upscale() {
    throw new Error('Upscale por IA requer um provider externo configurado.');
  }

  async outpaint() {
    throw new Error('Outpainting por IA requer um provider externo configurado.');
  }
}

export const aiProvider = new AIImageProvider();
