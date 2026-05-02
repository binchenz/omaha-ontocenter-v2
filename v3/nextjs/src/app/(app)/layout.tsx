import AppLayout from "@/components/layout/AppLayout";
import Providers from "@/components/layout/Providers";

export default function Layout({ children }: { children: React.ReactNode }) {
  return (
    <Providers>
      <AppLayout>{children}</AppLayout>
    </Providers>
  );
}
