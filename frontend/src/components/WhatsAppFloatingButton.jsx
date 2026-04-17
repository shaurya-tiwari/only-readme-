import { useTranslation } from "react-i18next";
import { useAuth } from "../auth/AuthContext";

/**
 * Premium floating WhatsApp button.
 * Triggers the start of the WhatsApp mini-app (onboarding & support).
 */
export default function WhatsAppFloatingButton() {
  const { t } = useTranslation();
  const { isAuthenticated, role } = useAuth();
  
  // Real Meta display number
  const whatsappNumber = "15551908959"; 
  const waLink = `https://wa.me/${whatsappNumber}?text=hi`;

  // Hide button for admin users or during specific states if desired
  if (isAuthenticated && role === "admin") return null;

  return (
    <div className="fixed bottom-6 right-6 z-[100] group">
      {/* Tooltip */}
      <div className="absolute bottom-full right-0 mb-4 opacity-0 group-hover:opacity-100 transition-all duration-300 translate-y-2 group-hover:translate-y-0 pointer-events-none">
        <div className="glass-card-3d px-4 py-2 whitespace-nowrap text-sm font-semibold shadow-2xl">
          {t("whatsapp.tooltip")}
          <div className="absolute top-full right-6 w-3 h-3 rotate-45 border-r border-b border-white/10 dark:border-white/5 bg-white/90 dark:bg-neutral-900/90 -mt-1.5" />
        </div>
      </div>

      {/* Button */}
      <a
        href={waLink}
        target="_blank"
        rel="noopener noreferrer"
        className="flex h-16 w-16 items-center justify-center rounded-full bg-[#25D366] text-white shadow-2xl transition-all duration-500 hover:scale-110 hover:shadow-[#25D366]/40 active:scale-95 animate-pulse-emerald overflow-hidden relative group/btn"
        aria-label={t("whatsapp.chat_on")}
      >
        {/* Glow effect */}
        <div className="absolute inset-0 bg-gradient-to-tr from-emerald-600 via-[#25D366] to-emerald-300 opacity-0 group-hover/btn:opacity-100 transition-opacity" />
        
        <svg
          viewBox="0 0 448 512"
          width="32"
          height="32"
          fill="currentColor"
          className="relative z-10"
          xmlns="http://www.w3.org/2000/svg"
        >
          <path d="M380.9 97.1C339 55.1 283.2 32 223.9 32c-122.4 0-222 99.6-222 222 0 39.1 10.2 77.3 29.6 111L0 480l117.7-30.9c32.4 17.7 68.9 27 106.1 27h.1c122.3 0 224.1-99.6 224.1-222 0-59.3-25.2-115-67.1-157zm-157 341.6c-33.1 0-65.6-8.9-93.7-25.7l-6.7-4-69.6 18.3 18.6-68-4.4-7c-18.5-29.4-28.2-63.3-28.2-98.2 0-101.7 82.8-184.5 184.6-184.5 49.3 0 95.6 19.2 130.4 54.1 34.8 34.9 56.2 81.2 56.1 130.5 0 101.8-84.9 184.6-186.6 184.6zm101.2-138.2c-5.5-2.8-32.8-16.2-37.9-18-5.1-1.9-8.8-2.8-12.5 2.8-3.7 5.6-14.3 18-17.6 21.8-3.2 3.7-6.5 4.2-12 1.4-5.5-2.8-23.2-8.5-44.2-27.1-16.4-14.6-27.4-32.7-30.6-38.1-3.2-5.5-.3-8.5 2.5-11.3 2.5-2.5 5.5-6.5 8.3-9.7 2.8-3.3 3.7-5.6 5.5-9.3 1.8-3.7.9-6.9-.5-9.7-1.4-2.8-12.5-30.1-17.1-41.2-4.5-10.8-9.1-9.3-12.5-9.5-3.2-.2-6.9-.2-10.6-.2-3.7 0-9.7 1.4-14.8 6.9-5.1 5.6-19.4 19-19.4 46.3 0 27.3 19.9 53.7 22.6 57.4 2.8 3.7 39.1 59.7 94.8 83.8 13.3 5.7 23.7 9.1 31.7 11.7 13.3 4.2 25.4 3.6 35 2.2 10.7-1.6 32.8-13.4 37.4-26.4 4.6-13 4.6-24.1 3.2-26.4-1.3-2.5-5-3.9-10.5-6.6z" />
        </svg>
      </a>
    </div>
  );
}
