/** Nomes amigáveis para os tipos de ação mais comuns das plataformas. O código original
 *  aparece sempre embaixo, porque cada conta pode ter ações próprias (eventos personalizados). */
const ROTULOS: Record<string, string> = {
  purchase: "Compra",
  "offsite_conversion.fb_pixel_purchase": "Compra (pixel)",
  "onsite_web_purchase": "Compra no site",
  "omni_purchase": "Compra (todos os canais)",
  lead: "Lead",
  "offsite_conversion.fb_pixel_lead": "Lead (pixel)",
  "onsite_conversion.lead_grouped": "Lead de formulário",
  "leadgen_grouped": "Lead de formulário",
  "onsite_conversion.messaging_conversation_started_7d": "Conversa iniciada por mensagem",
  "onsite_conversion.total_messaging_connection": "Conexão por mensagem",
  complete_registration: "Cadastro concluído",
  "offsite_conversion.fb_pixel_complete_registration": "Cadastro concluído (pixel)",
  add_to_cart: "Adicionou ao carrinho",
  "offsite_conversion.fb_pixel_add_to_cart": "Adicionou ao carrinho (pixel)",
  initiate_checkout: "Iniciou a finalização da compra",
  "offsite_conversion.fb_pixel_initiate_checkout": "Iniciou a finalização (pixel)",
  add_payment_info: "Adicionou forma de pagamento",
  view_content: "Visualizou conteúdo",
  "offsite_conversion.fb_pixel_view_content": "Visualizou conteúdo (pixel)",
  contact: "Contato",
  schedule: "Agendamento",
  submit_application: "Envio de inscrição",
  subscribe: "Assinatura",
  landing_page_view: "Visualização da página de destino",
  link_click: "Clique no link",
  post_engagement: "Engajamento com a publicação",
  page_engagement: "Engajamento com a página",
  video_view: "Visualização de vídeo",
  conversions: "Conversões principais da conta",
  all_conversions: "Todas as conversões",
  external_website_conversions: "Conversões no site",
  conversion: "Conversões",
  complete_payment: "Pagamento concluído",
};

export const JANELA_LABEL: Record<string, string> = {
  "1d_click": "1 dia após o clique",
  "7d_click": "7 dias após o clique",
  "28d_click": "28 dias após o clique",
  "1d_view": "1 dia após a visualização",
};

export function rotuloAcao(tipo: string): string {
  return ROTULOS[tipo] ?? tipo.replace(/^offsite_conversion\.(fb_pixel_)?/, "").replace(/[._]/g, " ");
}
