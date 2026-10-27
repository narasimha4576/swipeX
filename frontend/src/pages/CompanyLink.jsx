import { useState } from "react";
import TrustSheet from "./TrustSheet";

export default function CompanyLink({ company }) {
  const [open, setOpen] = useState(false);

  return (
    <>
      <button
        type="button"
        className="company-link"
        onPointerDownCapture={(e) => e.stopPropagation()}
        onClick={() => setOpen(true)}
      >
        {company.name}
        <svg
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <path d="M12 3l8 3v6c0 5-3.5 8-8 9-4.5-1-8-4-8-9V6l8-3z" />
          <path d="M9 12l2 2 4-4" />
        </svg>
      </button>
      {open && <TrustSheet companyId={company.id} onClose={() => setOpen(false)} />}
    </>
  );
}