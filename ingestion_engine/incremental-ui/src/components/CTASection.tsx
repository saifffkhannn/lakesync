export default function CTASection() {
  return (
    <div className="bg-white py-16 sm:py-24">
      <div className="mx-auto max-w-7xl px-6 lg:px-16">
        <div className="relative isolate overflow-hidden bg-gradient-to-br from-blue-50 to-indigo-50 px-6 pt-16 shadow-md sm:rounded-3xl sm:px-16 md:pt-24 lg:flex lg:gap-x-20 lg:px-24 lg:pt-0 border border-blue-100">
          <div className="mx-auto max-w-md text-center lg:mx-0 lg:flex-auto lg:py-32 lg:text-left">
            <h2 className="text-sm font-semibold uppercase tracking-wider text-gray-500 mb-2">
              CTA Banner
            </h2>
            <h2 className="text-3xl font-bold tracking-tight text-gray-900 sm:text-4xl text-left">
              Ready to simplify your<br />data pipelines?
            </h2>
            <div className="mt-10 flex items-center justify-center gap-x-6 lg:justify-start">
              <a
                href="#"
                className="rounded-lg bg-blue-500 px-6 py-3.5 text-sm font-semibold text-white shadow-sm hover:focus-visible:outline hover:focus-visible:outline-2 hover:focus-visible:outline-offset-2 hover:focus-visible:outline-blue-600 transition-colors"
              >
                Get Started Now
              </a>
            </div>
          </div>
          <div className="relative mt-16 h-80 lg:mt-8">
            <img
              className="absolute left-0 top-0 w-[57rem] max-w-none rounded-md bg-white/5 ring-1 ring-white/10"
              src="https://tailwindui.com/img/component-images/dark-project-app-screenshot.png"
              alt="App screenshot"
              width={1824}
              height={1080}
            />
          </div>
        </div>
      </div>
    </div>
  );
}
