export default function Head() {
  const faqSchema = {
    "@context": "https://schema.org",
    "@type": "FAQPage",
    mainEntity: [
      {
        "@type": "Question",
        name: "Jarvis internet baglantisi gerektiriyor mu?",
        acceptedAnswer: {
          "@type": "Answer",
          text: "Hayir, tamamen lokal calisir."
        }
      },
      {
        "@type": "Question",
        name: "Telegram botu nasil kurulur?",
        acceptedAnswer: {
          "@type": "Answer",
          text: "Kurulumda sana adim adim yol gosteriyoruz."
        }
      },
      {
        "@type": "Question",
        name: "Verilerim nerede saklanir?",
        acceptedAnswer: {
          "@type": "Answer",
          text: "Kendi bilgisayarinda, hicbir yere gonderilmez."
        }
      },
      {
        "@type": "Question",
        name: "Iptal edebilir miyim?",
        acceptedAnswer: {
          "@type": "Answer",
          text: "Evet, istedigin zaman."
        }
      },
      {
        "@type": "Question",
        name: "Kac kisi kullanabilir?",
        acceptedAnswer: {
          "@type": "Answer",
          text: "Paketlere gore 1-sinirsiz bot."
        }
      }
    ]
  };

  return (
    <script
      type="application/ld+json"
      dangerouslySetInnerHTML={{ __html: JSON.stringify(faqSchema) }}
    />
  );
}
